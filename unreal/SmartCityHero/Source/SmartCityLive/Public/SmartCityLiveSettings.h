#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "SmartCityLiveSettings.generated.h"

/**
 * 3080 Ti hero-ring live link. Unreal is the camera; SUMO owns traffic.
 * I-88 extra lane is a bioswale + AV strip, not asphalt.
 */
UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="Smart City Live"))
class SMARTCITYLIVE_API USmartCityLiveSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	virtual FName GetCategoryName() const override { return FName(TEXT("SmartCity")); }

	UPROPERTY(Config, EditAnywhere, Category="Backend")
	FString BackendBaseUrl = TEXT("http://127.0.0.1:43147");

	UPROPERTY(Config, EditAnywhere, Category="Backend")
	FString TwinPath = TEXT("/twin");

	UPROPERTY(Config, EditAnywhere, Category="Backend")
	FString WebSocketPath = TEXT("/ws");

	/** Downtown Naperville. Twin catalog / Cesium origin. UTM 16N. */
	UPROPERTY(Config, EditAnywhere, Category="Georef")
	double OriginLongitude = -88.147;

	UPROPERTY(Config, EditAnywhere, Category="Georef")
	double OriginLatitude = 41.75;

	UPROPERTY(Config, EditAnywhere, Category="Georef")
	FString OriginCrs = TEXT("EPSG:32616");

	UPROPERTY(Config, EditAnywhere, Category="Streaming", meta=(ClampMin="64", ClampMax="1024"))
	int32 WorldPartitionCellMeters = 256;

	UPROPERTY(Config, EditAnywhere, Category="Streaming")
	float HeroRadiusMeters = 1500.f;

	UPROPERTY(Config, EditAnywhere, Category="Streaming")
	float ImpostorRadiusMeters = 8000.f;

	/** Skeletal cars only inside ~80-120 m. Default 100. */
	UPROPERTY(Config, EditAnywhere, Category="Hero Traffic", meta=(ClampMin="80", ClampMax="120"))
	float SkeletalCarCullMeters = 100.f;

	/** Stub stays off: do not spawn 400k AActors. */
	UPROPERTY(Config, EditAnywhere, Category="Hero Traffic")
	bool bSpawnSkeletalCars = false;
};
