#include "SmartCityLive.h"

#define LOCTEXT_NAMESPACE "FSmartCityLiveModule"

DEFINE_LOG_CATEGORY(LogSmartCityLive);

void FSmartCityLiveModule::StartupModule()
{
	UE_LOG(LogSmartCityLive, Log,
		TEXT("SmartCityLive: Unreal is the camera (not Unity). Origin -88.147, 41.75 UTM 16N. glTF -> /Game/City/Naperville/Import"));
}

void FSmartCityLiveModule::ShutdownModule()
{
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_PRIMARY_GAME_MODULE(FSmartCityLiveModule, SmartCityLive, "SmartCityHero");
