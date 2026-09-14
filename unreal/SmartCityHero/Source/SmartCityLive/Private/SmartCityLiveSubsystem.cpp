#include "SmartCityLiveSubsystem.h"

#include "SmartCityLive.h"
#include "SmartCityLiveSettings.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HttpModule.h"
#include "IWebSocket.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "WebSocketsModule.h"

void USmartCityLiveSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	FetchTwin();
	ConnectWebSocket();
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateUObject(this, &USmartCityLiveSubsystem::PollTwin),
		2.0f);
}

void USmartCityLiveSubsystem::Deinitialize()
{
	if (TickHandle.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
		TickHandle.Reset();
	}
	if (Socket.IsValid())
	{
		Socket->OnMessage().Clear();
		if (Socket->IsConnected())
		{
			Socket->Close();
		}
		Socket.Reset();
	}
	Super::Deinitialize();
}

bool USmartCityLiveSubsystem::PollTwin(float /*DeltaTime*/)
{
	FetchTwin();
	return true;
}

FVector USmartCityLiveSubsystem::LonLatToUnrealCm(double Longitude, double Latitude) const
{
	const USmartCityLiveSettings* Settings = GetDefault<USmartCityLiveSettings>();
	const double CosLat = FMath::Cos(FMath::DegreesToRadians(Settings->OriginLatitude));
	const double EastM = (Longitude - Settings->OriginLongitude) * 111320.0 * CosLat;
	const double NorthM = (Latitude - Settings->OriginLatitude) * 110540.0;
	return FVector(EastM * 100.0, NorthM * 100.0, 0.0);
}

void USmartCityLiveSubsystem::FetchTwin()
{
	const USmartCityLiveSettings* Settings = GetDefault<USmartCityLiveSettings>();
	FString Base = Settings->BackendBaseUrl;
	while (Base.EndsWith(TEXT("/")))
	{
		Base.LeftChopInline(1);
	}
	const FString Url = Base + Settings->TwinPath;

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Request->SetVerb(TEXT("GET"));
	Request->SetURL(Url);
	Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
	Request->OnProcessRequestComplete().BindUObject(this, &USmartCityLiveSubsystem::OnTwinResponse);
	Request->ProcessRequest();
}

void USmartCityLiveSubsystem::OnTwinResponse(FHttpRequestPtr /*Request*/, FHttpResponsePtr Response, bool bSucceeded)
{
	if (!bSucceeded || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
	{
		if (!bLoggedBackendError)
		{
			UE_LOG(LogSmartCityLive, Warning,
				TEXT("GET /twin failed. Start `smartcity serve --port 43147`. Unreal will not invent traffic."));
			bLoggedBackendError = true;
		}
		return;
	}
	bLoggedBackendError = false;
	ApplyTwinJson(Response->GetContentAsString());
}

void USmartCityLiveSubsystem::ConnectWebSocket()
{
	const USmartCityLiveSettings* Settings = GetDefault<USmartCityLiveSettings>();
	FString Base = Settings->BackendBaseUrl;
	Base.ReplaceInline(TEXT("https://"), TEXT("wss://"));
	Base.ReplaceInline(TEXT("http://"), TEXT("ws://"));
	while (Base.EndsWith(TEXT("/")))
	{
		Base.LeftChopInline(1);
	}
	const FString Url = Base + Settings->WebSocketPath;

	if (!FModuleManager::Get().IsModuleLoaded(TEXT("WebSockets")))
	{
		FModuleManager::LoadModuleChecked<FWebSocketsModule>(TEXT("WebSockets"));
	}

	if (Socket.IsValid())
	{
		Socket->Close();
		Socket.Reset();
	}

	Socket = FWebSocketsModule::Get().CreateWebSocket(Url, TEXT(""));
	Socket->OnConnected().AddLambda([]()
	{
		UE_LOG(LogSmartCityLive, Log, TEXT("WS /ws connected"));
	});
	Socket->OnConnectionError().AddLambda([this](const FString& Error)
	{
		if (!bLoggedBackendError)
		{
			UE_LOG(LogSmartCityLive, Warning, TEXT("WS /ws error: %s"), *Error);
			bLoggedBackendError = true;
		}
	});
	Socket->OnMessage().AddUObject(this, &USmartCityLiveSubsystem::OnWsMessage);
	Socket->Connect();
}

void USmartCityLiveSubsystem::OnWsMessage(const FString& Message)
{
	ApplyTwinJson(Message);
}

void USmartCityLiveSubsystem::ApplyTwinJson(const FString& Json)
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return;
	}

	TSharedPtr<FJsonObject> Twin = Root;
	const TSharedPtr<FJsonObject>* NestedTwin = nullptr;
	if (Root->TryGetObjectField(TEXT("twin"), NestedTwin) && NestedTwin && NestedTwin->IsValid())
	{
		Twin = *NestedTwin;
	}

	Root->TryGetStringField(TEXT("clock"), LastSnapshot.Clock);
	Twin->TryGetStringField(TEXT("clock"), LastSnapshot.Clock);
	Twin->TryGetStringField(TEXT("weekday_name"), LastSnapshot.WeekdayName);

	const TArray<TSharedPtr<FJsonValue>>* Lanes = nullptr;
	if (Twin->TryGetArrayField(TEXT("lanes"), Lanes) && Lanes)
	{
		for (const TSharedPtr<FJsonValue>& LaneVal : *Lanes)
		{
			const TSharedPtr<FJsonObject> Lane = LaneVal->AsObject();
			if (!Lane.IsValid())
			{
				continue;
			}
			FString Id;
			Lane->TryGetStringField(TEXT("id"), Id);
			if (Id != TEXT("i88-solarpunk"))
			{
				continue;
			}
			Lane->TryGetStringField(TEXT("direction"), LastSnapshot.I88Direction);
			int32 ExtraLanes = 0;
			Lane->TryGetNumberField(TEXT("extra_lanes"), ExtraLanes);
			LastSnapshot.bI88BioswaleActive = ExtraLanes > 0;
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* Vehicles = nullptr;
	if (Root->TryGetArrayField(TEXT("vehicles"), Vehicles))
	{
		ApplyVehicleArray(Vehicles);
	}

	OnTwinUpdated.Broadcast(LastSnapshot);
}

void USmartCityLiveSubsystem::ApplyVehicleArray(const TArray<TSharedPtr<FJsonValue>>* Vehicles)
{
	const USmartCityLiveSettings* Settings = GetDefault<USmartCityLiveSettings>();
	const float CullCm = Settings->SkeletalCarCullMeters * 100.f;
	int32 Total = 0;
	int32 Hero = 0;
	if (Vehicles)
	{
		for (const TSharedPtr<FJsonValue>& Value : *Vehicles)
		{
			const TSharedPtr<FJsonObject> Car = Value->AsObject();
			if (!Car.IsValid())
			{
				continue;
			}
			++Total;
			double Lon = 0.0;
			double Lat = 0.0;
			if (!Car->TryGetNumberField(TEXT("lon"), Lon) || !Car->TryGetNumberField(TEXT("lat"), Lat))
			{
				continue;
			}
			const FVector Cm = LonLatToUnrealCm(Lon, Lat);
			if (Cm.Size2D() <= CullCm)
			{
				++Hero;
			}
		}
	}
	LastSnapshot.WsVehicleCount = Total;
	LastSnapshot.HeroVehicleCount = Hero;
	// Skeletal meshes only inside 80-120 m, and only when bSpawnSkeletalCars is on.
	// This stub never spawns. Meso ribbons are Mass/Niagara, not AActors.
}
