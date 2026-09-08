plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.livekey.mobilekeyboard"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.livekey.mobilekeyboard"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

kotlin {
    jvmToolchain(17)
}
