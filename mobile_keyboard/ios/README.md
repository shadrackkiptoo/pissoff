# iPhone Keyboard Extension

Add `LiveKeyKeyboard.swift` to a **Custom Keyboard Extension** target in Xcode.
Set the service URL near the bottom of the file, then enable the keyboard in:

`Settings > General > Keyboard > Keyboards > Add New Keyboard`

The `SEND` key requires **Allow Full Access** because it makes the explicit API
request. The keyboard does not monitor other apps or upload individual keys.

An iOS build and signing step requires macOS and Xcode. Windows can hold and
edit this source, but cannot produce the signed iPhone executable.
