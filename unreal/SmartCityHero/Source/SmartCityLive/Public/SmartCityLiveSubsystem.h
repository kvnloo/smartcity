#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "SmartCityLiveSubsystem.generated.h"

class IWebSocket;
class FJsonValue;

USTRUCT(BlueprintType)
struct FSmartCityTwinSnapshot
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	FString Clock;

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	FString WeekdayName;

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	FString I88Direction;

	/** Extra I-88 lane as bioswale + AV chevrons. Never extra asphalt. */
	UPROPERTY(BlueprintReadOnly, Category="Twin")
	bool bI88BioswaleActive = false;

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	int32 WsVehicleCount = 0;

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	int32 HeroVehicleCount = 0;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSmartCityTwinUpdated, FSmartCityTwinSnapshot, Snapshot);

/**
 * Polls GET /twin and WS /ws. Counts hero-ring vehicles; does not tick SUMO.
 */
UCLASS()
class SMARTCITYLIVE_API USmartCityLiveSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	UPROPERTY(BlueprintAssignable, Category="Twin")
	FOnSmartCityTwinUpdated OnTwinUpdated;

	UPROPERTY(BlueprintReadOnly, Category="Twin")
	FSmartCityTwinSnapshot LastSnapshot;

	/** East=+X, north=+Y, centimetres. Origin from SmartCityLiveSettings. */
	UFUNCTION(BlueprintPure, Category="Georef")
	FVector LonLatToUnrealCm(double Longitude, double Latitude) const;

	UFUNCTION(BlueprintCallable, Category="Twin")
	void FetchTwin();

	UFUNCTION(BlueprintCallable, Category="Twin")
	void ConnectWebSocket();

private:
	void OnTwinResponse(FHttpRequestPtr Request, FHttpResponsePtr Response, bool bSucceeded);
	void OnWsMessage(const FString& Message);
	void ApplyTwinJson(const FString& Json);
	void ApplyVehicleArray(const TArray<TSharedPtr<FJsonValue>>* Vehicles);
	bool PollTwin(float DeltaTime);

	TSharedPtr<IWebSocket> Socket;
	FTSTicker::FDelegateHandle TickHandle;
	bool bLoggedBackendError = false;
};
