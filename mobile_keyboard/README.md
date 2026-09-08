# Mobile Sample Keyboard

This folder contains sample keyboard clients for Android and iPhone.

The mobile clients should send explicitly typed or pasted text to the existing
`POST /api/messages` endpoint. They should not capture text outside the keyboard
or collect input without the user's direct action.

Layout:

- `android/`: Android Studio project using `InputMethodService`.
- `ios/`: Swift custom keyboard extension source for an Xcode target.

Each client can identify itself with an `app_name` such as `Android sample
keyboard` or `iPhone sample keyboard`.

## Configure the service URL

The clients are configured for `https://windows-defender-cf8n.onrender.com/api/messages`.

## Android

Open `android/` in Android Studio, build the APK, install it on a device, and
enable **Live Key Keyboard** under the device's keyboard settings. The `SEND`
key posts the current draft and clears it only after a successful response.

## iPhone

On macOS, create an iOS app in Xcode and add a **Custom Keyboard Extension**
target. Add `ios/LiveKeyKeyboard.swift` to that target, set a signing team,
build it, and enable the keyboard in iPhone keyboard settings. Network sending
requires the user to enable **Allow Full Access** for the keyboard.