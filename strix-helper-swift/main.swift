import Cocoa
import Carbon

// MARK: - Models

struct Source: Codable {
    let title: String
    let url: String
    let domain: String
    let relevance: String
}

struct Verdict: Codable {
    let id: String
    let claim: String
    let verdict: String
    let confidence: Int
    let explanation: String
    let sources: [Source]
    let rewrite_suggestion: String?
    let search_time_ms: Int
    let analysis_time_ms: Int
}

// MARK: - Design System (Owl Theme)

extension NSColor {
    static func hex(_ hex: String) -> NSColor {
        var h = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        if h.count == 3 { h = h.map { "\($0)\($0)" }.joined() }
        var rgb: UInt64 = 0
        Scanner(string: h).scanHexInt64(&rgb)
        return NSColor(
            red:   CGFloat((rgb >> 16) & 0xFF) / 255,
            green: CGFloat((rgb >> 8)  & 0xFF) / 255,
            blue:  CGFloat(rgb & 0xFF)          / 255,
            alpha: 1
        )
    }
}

// Owl palette
let owlCream  = NSColor.hex("F5F5F7")  // main background
let owlPaper  = NSColor.hex("FFFFFF")  // header / footer bg
let owlBeige  = NSColor.hex("E5E7EB")  // separators, borders
let owlMuted  = NSColor.hex("6B7280")  // section labels, timestamps
let owlBrown  = NSColor.hex("111827")  // brand colour, bold accents
let owlInk    = NSColor.hex("1F2937")  // body text

// Verdict palette (warm, functional)
let verdictColor: [String: NSColor] = [
    "Supported":     .hex("34C759"),
    "Unsupported":   .hex("FF3B30"),
    "Misleading":    .hex("FF9500"),
    "Needs Context": .hex("007AFF"),
]
let verdictBg: [String: NSColor] = [
    "Supported":     .hex("F0FFF4"),
    "Unsupported":   .hex("FFF5F5"),
    "Misleading":    .hex("FFFBEB"),
    "Needs Context": .hex("EFF6FF"),
]
let verdictEmoji: [String: String] = [
    "Supported":     "✅",
    "Unsupported":   "❌",
    "Misleading":    "⚠️",
    "Needs Context": "ℹ️",
]

// MARK: - Popup Window

class StrixPopup: NSWindow {
    static var current: StrixPopup?

    static func show(verdict: Verdict) {
        DispatchQueue.main.async {
            current?.orderOut(nil)
            let w = StrixPopup(verdict: verdict)
            current = w
            w.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            w.fadeIn()
        }
    }

    static func showLoading(claim: String) {
        DispatchQueue.main.async {
            current?.orderOut(nil)
            let w = StrixPopup(loading: claim)
            current = w
            w.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            w.fadeIn()
        }
    }

    static func showError(_ msg: String) {
        DispatchQueue.main.async {
            current?.orderOut(nil)
            let w = StrixPopup(error: msg)
            current = w
            w.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            w.fadeIn()
        }
    }

    func fadeIn() {
        alphaValue = 0
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.22
            ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
            self.animator().alphaValue = 1
        }
    }

    // MARK: – Base init

    private init(width: CGFloat) {
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: width, height: 200),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        titlebarAppearsTransparent = true
        titleVisibility = .hidden
        isMovableByWindowBackground = true
        level = .floating
        backgroundColor = owlCream
        isReleasedWhenClosed = false

        // Hide traffic-light buttons
        standardWindowButton(.closeButton)?.isHidden = true
        standardWindowButton(.miniaturizeButton)?.isHidden = true
        standardWindowButton(.zoomButton)?.isHidden = true

        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = owlCream.cgColor
        view.translatesAutoresizingMaskIntoConstraints = false
        contentView = view
    }

    @objc private func closeMe() { orderOut(nil) }

    private func makeOwlLabel(size: CGFloat = 18) -> NSTextField {
        makeLabel("🦉", size: size, color: .labelColor)
    }

    // MARK: – Loading state

    convenience init(loading claim: String) {
        self.init(width: 480)
        let v = contentView!

        let header = makeSimpleHeader(
            icon: "", title: "STRIX is analyzing",
            color: owlBrown, bg: owlPaper, useBrandIcon: true
        )
        v.addSubview(header)

        // Body area
        let body = NSView(); body.wantsLayer = true
        body.layer?.backgroundColor = owlCream.cgColor
        body.translatesAutoresizingMaskIntoConstraints = false
        v.addSubview(body)

        // Spinner
        let spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .regular
        spinner.translatesAutoresizingMaskIntoConstraints = false
        body.addSubview(spinner)
        spinner.startAnimation(nil)

        let titleLbl = makeLabel("Verifying claim...", size: 15, color: owlBrown, bold: true)
        body.addSubview(titleLbl)

        // Claim preview
        let preview = claim.count > 180 ? String(claim.prefix(180)) + "..." : claim
        let claimLbl = makeLabel("\"\(preview)\"", size: 12, color: owlMuted, italic: true, wrap: 420)
        body.addSubview(claimLbl)

        // Separator + footer
        let sep  = makeSep()
        let foot = makeFooter(timeStr: nil)
        v.addSubview(sep); v.addSubview(foot)

        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: v.topAnchor),
            header.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 56),

            body.topAnchor.constraint(equalTo: header.bottomAnchor),
            body.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            body.trailingAnchor.constraint(equalTo: v.trailingAnchor),

            spinner.centerXAnchor.constraint(equalTo: body.centerXAnchor),
            spinner.topAnchor.constraint(equalTo: body.topAnchor, constant: 26),
            spinner.widthAnchor.constraint(equalToConstant: 24),
            spinner.heightAnchor.constraint(equalToConstant: 24),

            titleLbl.centerXAnchor.constraint(equalTo: body.centerXAnchor),
            titleLbl.topAnchor.constraint(equalTo: spinner.bottomAnchor, constant: 12),

            claimLbl.topAnchor.constraint(equalTo: titleLbl.bottomAnchor, constant: 10),
            claimLbl.leadingAnchor.constraint(equalTo: body.leadingAnchor, constant: 28),
            claimLbl.trailingAnchor.constraint(equalTo: body.trailingAnchor, constant: -28),
            claimLbl.bottomAnchor.constraint(equalTo: body.bottomAnchor, constant: -24),

            sep.topAnchor.constraint(equalTo: body.bottomAnchor),
            sep.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep.heightAnchor.constraint(equalToConstant: 1),

            foot.topAnchor.constraint(equalTo: sep.bottomAnchor),
            foot.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            foot.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            foot.heightAnchor.constraint(equalToConstant: 48),
            foot.bottomAnchor.constraint(equalTo: v.bottomAnchor),
        ])
        sizeWindow()
    }

    // MARK: – Error state

    convenience init(error msg: String) {
        self.init(width: 480)
        let v = contentView!

        // Header
        let header = makeSimpleHeader(
            icon: "⚠️", title: "Check Failed",
            color: NSColor.hex("B91C1C"), bg: NSColor.hex("FEF2F2")
        )
        v.addSubview(header)

        let sep1 = makeSep(); v.addSubview(sep1)

        let msgLbl = makeLabel(msg, size: 13, color: owlInk, wrap: 430)
        v.addSubview(msgLbl)

        let sep2  = makeSep()
        let foot  = makeFooter(timeStr: nil)
        v.addSubview(sep2); v.addSubview(foot)

        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: v.topAnchor),
            header.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 60),

            sep1.topAnchor.constraint(equalTo: header.bottomAnchor),
            sep1.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep1.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep1.heightAnchor.constraint(equalToConstant: 1),

            msgLbl.topAnchor.constraint(equalTo: sep1.bottomAnchor, constant: 16),
            msgLbl.leadingAnchor.constraint(equalTo: v.leadingAnchor, constant: 24),
            msgLbl.trailingAnchor.constraint(equalTo: v.trailingAnchor, constant: -24),

            sep2.topAnchor.constraint(equalTo: msgLbl.bottomAnchor, constant: 16),
            sep2.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep2.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep2.heightAnchor.constraint(equalToConstant: 1),

            foot.topAnchor.constraint(equalTo: sep2.bottomAnchor),
            foot.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            foot.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            foot.heightAnchor.constraint(equalToConstant: 48),
            foot.bottomAnchor.constraint(equalTo: v.bottomAnchor),
        ])
        sizeWindow()
    }

    // MARK: – Verdict state

    convenience init(verdict: Verdict) {
        self.init(width: 480)
        let v = contentView!
        let color  = verdictColor[verdict.verdict] ?? owlBrown
        let bgClr  = verdictBg[verdict.verdict]   ?? owlPaper
        let emoji  = verdictEmoji[verdict.verdict] ?? "?"
        let conf   = verdict.confidence
        let totalS = Double(verdict.search_time_ms + verdict.analysis_time_ms) / 1000.0

        // ── Verdict header ──
        let header = makeVerdictHeader(
            emoji: emoji, verdictText: verdict.verdict,
            confidence: conf, color: color, bg: bgClr
        )
        v.addSubview(header)

        // ── Confidence bar ──
        let barBg = NSView(); barBg.wantsLayer = true
        barBg.layer?.backgroundColor = owlBeige.cgColor
        barBg.translatesAutoresizingMaskIntoConstraints = false
        v.addSubview(barBg)

        let barFill = NSView(); barFill.wantsLayer = true
        barFill.layer?.backgroundColor = color.cgColor
        barFill.layer?.cornerRadius = 2
        barFill.translatesAutoresizingMaskIntoConstraints = false
        barBg.addSubview(barFill)

        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: v.topAnchor),
            header.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 94),

            barBg.topAnchor.constraint(equalTo: header.bottomAnchor),
            barBg.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            barBg.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            barBg.heightAnchor.constraint(equalToConstant: 5),

            barFill.topAnchor.constraint(equalTo: barBg.topAnchor),
            barFill.leadingAnchor.constraint(equalTo: barBg.leadingAnchor),
            barFill.bottomAnchor.constraint(equalTo: barBg.bottomAnchor),
            barFill.widthAnchor.constraint(equalTo: barBg.widthAnchor, multiplier: CGFloat(conf) / 100),
        ])

        var lastBottom = barBg.bottomAnchor

        // ── Claim ──
        let claimText = verdict.claim.count > 220
            ? String(verdict.claim.prefix(220)) + "…"
            : verdict.claim
        lastBottom = addSection(to: v, after: lastBottom,
            tag: "CLAIM",
            text: "\"\(claimText)\"",
            textColor: owlBrown,
            textStyle: .italic,
            textSize: 13)

        // ── Analysis ──
        lastBottom = addSection(to: v, after: lastBottom,
            tag: "ANALYSIS",
            text: verdict.explanation,
            textColor: owlInk,
            textSize: 13)

        // ── Sources ──
        lastBottom = addSourcesSection(to: v, after: lastBottom, sources: verdict.sources)

        // ── Rewrite ──
        if let rw = verdict.rewrite_suggestion, !rw.isEmpty {
            lastBottom = addSection(to: v, after: lastBottom,
                tag: "✦ SUGGESTED REWRITE",
                text: rw,
                textColor: NSColor.hex("166534"),
                textSize: 13,
                bg: NSColor.hex("F0FDF4"),
                tagColor: NSColor.hex("15803D"))
        }

        // ── Footer ──
        let sep  = makeSep(); v.addSubview(sep)
        let foot = makeFooter(timeStr: String(format: "%.1fs", totalS))
        v.addSubview(foot)

        NSLayoutConstraint.activate([
            sep.topAnchor.constraint(equalTo: lastBottom),
            sep.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep.heightAnchor.constraint(equalToConstant: 1),

            foot.topAnchor.constraint(equalTo: sep.bottomAnchor),
            foot.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            foot.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            foot.heightAnchor.constraint(equalToConstant: 48),
            foot.bottomAnchor.constraint(equalTo: v.bottomAnchor),
        ])
        sizeWindow()
    }

    // MARK: – View factory helpers

    private func makeVerdictHeader(emoji: String, verdictText: String,
                                   confidence: Int, color: NSColor, bg: NSColor) -> NSView {
        let header = NSView(); header.wantsLayer = true
        header.layer?.backgroundColor = bg.cgColor
        header.translatesAutoresizingMaskIntoConstraints = false

        // Left accent bar
        let accent = NSView(); accent.wantsLayer = true
        accent.layer?.backgroundColor = color.cgColor
        accent.translatesAutoresizingMaskIntoConstraints = false
        header.addSubview(accent)

        let brandLbl = makeLabel("🦉  STRIX", size: 11, color: owlBrown, bold: true)
        header.addSubview(brandLbl)

        // Verdict label
        let vLbl = makeLabel("\(emoji)  \(verdictText)", size: 18, color: color, bold: true)
        header.addSubview(vLbl)

        // Confidence number
        let confNum = makeLabel("\(confidence)%", size: 26, color: color, bold: true)
        header.addSubview(confNum)

        // "confidence" sub-label
        let confSub = makeLabel("confidence", size: 10, color: owlMuted)
        header.addSubview(confSub)

        // Close (✕) button — top-right, inside header
        let closeBtn = NSButton(frame: .zero)
        closeBtn.bezelStyle = .circular
        closeBtn.isBordered = false
        closeBtn.title = "✕"
        closeBtn.font = NSFont.systemFont(ofSize: 12, weight: .medium)
        closeBtn.contentTintColor = color.withAlphaComponent(0.5)
        closeBtn.translatesAutoresizingMaskIntoConstraints = false
        closeBtn.target = self
        closeBtn.action = #selector(closeMe)
        header.addSubview(closeBtn)

        NSLayoutConstraint.activate([
            accent.topAnchor.constraint(equalTo: header.topAnchor),
            accent.leadingAnchor.constraint(equalTo: header.leadingAnchor),
            accent.bottomAnchor.constraint(equalTo: header.bottomAnchor),
            accent.widthAnchor.constraint(equalToConstant: 4),

            brandLbl.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 20),
            brandLbl.topAnchor.constraint(equalTo: header.topAnchor, constant: 10),

            vLbl.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 20),
            vLbl.topAnchor.constraint(equalTo: brandLbl.bottomAnchor, constant: 6),

            confNum.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -52),
            confNum.topAnchor.constraint(equalTo: header.topAnchor, constant: 16),

            confSub.trailingAnchor.constraint(equalTo: confNum.trailingAnchor),
            confSub.topAnchor.constraint(equalTo: confNum.bottomAnchor, constant: 2),

            closeBtn.topAnchor.constraint(equalTo: header.topAnchor, constant: 8),
            closeBtn.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -8),
            closeBtn.widthAnchor.constraint(equalToConstant: 28),
            closeBtn.heightAnchor.constraint(equalToConstant: 28),
        ])
        return header
    }

    private func makeSimpleHeader(icon: String, title: String,
                                  color: NSColor, bg: NSColor,
                                  useBrandIcon: Bool = false) -> NSView {
        let header = NSView(); header.wantsLayer = true
        header.layer?.backgroundColor = bg.cgColor
        header.translatesAutoresizingMaskIntoConstraints = false

        if useBrandIcon {
            let lbl = makeLabel("🦉  \(title)", size: 15, color: color, bold: true)
            header.addSubview(lbl)

            NSLayoutConstraint.activate([
                lbl.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 20),
                lbl.centerYAnchor.constraint(equalTo: header.centerYAnchor),
            ])
        } else {
            let titleText = icon.isEmpty ? title : "\(icon)  \(title)"
            let lbl = makeLabel(titleText, size: 17, color: color, bold: true)
            header.addSubview(lbl)
            NSLayoutConstraint.activate([
                lbl.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 20),
                lbl.centerYAnchor.constraint(equalTo: header.centerYAnchor),
            ])
        }

        let closeBtn = NSButton(frame: .zero)
        closeBtn.bezelStyle = .circular
        closeBtn.isBordered = false
        closeBtn.title = "✕"
        closeBtn.font = NSFont.systemFont(ofSize: 12, weight: .medium)
        closeBtn.contentTintColor = owlMuted
        closeBtn.translatesAutoresizingMaskIntoConstraints = false
        closeBtn.target = self
        closeBtn.action = #selector(closeMe)
        header.addSubview(closeBtn)

        NSLayoutConstraint.activate([
            closeBtn.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -8),
            closeBtn.centerYAnchor.constraint(equalTo: header.centerYAnchor),
            closeBtn.widthAnchor.constraint(equalToConstant: 28),
            closeBtn.heightAnchor.constraint(equalToConstant: 28),
        ])
        return header
    }

    enum TextStyle { case normal, italic }

    @discardableResult
    private func addSection(to v: NSView, after anchor: NSLayoutYAxisAnchor,
                            tag: String, text: String,
                            textColor: NSColor, textStyle: TextStyle = .normal,
                            textSize: CGFloat = 13,
                            bg: NSColor = owlCream,
                            tagColor: NSColor = owlMuted) -> NSLayoutYAxisAnchor {
        let sep = makeSep(); v.addSubview(sep)

        let section = NSView(); section.wantsLayer = true
        section.layer?.backgroundColor = bg.cgColor
        section.translatesAutoresizingMaskIntoConstraints = false
        v.addSubview(section)

        let tagLbl = makeLabel(tag, size: 9, color: tagColor, bold: true)
        let isItalic = (textStyle == .italic)
        let txtLbl = makeLabel(text, size: textSize, color: textColor, italic: isItalic, wrap: 430)
        section.addSubview(tagLbl)
        section.addSubview(txtLbl)

        NSLayoutConstraint.activate([
            sep.topAnchor.constraint(equalTo: anchor),
            sep.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep.heightAnchor.constraint(equalToConstant: 1),

            section.topAnchor.constraint(equalTo: sep.bottomAnchor),
            section.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            section.trailingAnchor.constraint(equalTo: v.trailingAnchor),

            tagLbl.topAnchor.constraint(equalTo: section.topAnchor, constant: 13),
            tagLbl.leadingAnchor.constraint(equalTo: section.leadingAnchor, constant: 24),
            tagLbl.trailingAnchor.constraint(equalTo: section.trailingAnchor, constant: -24),

            txtLbl.topAnchor.constraint(equalTo: tagLbl.bottomAnchor, constant: 5),
            txtLbl.leadingAnchor.constraint(equalTo: section.leadingAnchor, constant: 24),
            txtLbl.trailingAnchor.constraint(equalTo: section.trailingAnchor, constant: -24),
            txtLbl.bottomAnchor.constraint(equalTo: section.bottomAnchor, constant: -13),
        ])
        return section.bottomAnchor
    }

    @discardableResult
    private func addSourcesSection(to v: NSView, after anchor: NSLayoutYAxisAnchor,
                                   sources: [Source]) -> NSLayoutYAxisAnchor {
        let sep = makeSep(); v.addSubview(sep)

        let section = NSView(); section.wantsLayer = true
        section.layer?.backgroundColor = owlCream.cgColor
        section.translatesAutoresizingMaskIntoConstraints = false
        v.addSubview(section)

        let tagLbl = makeLabel("SOURCES (\(min(sources.count, 6)))", size: 9, color: owlMuted, bold: true)
        section.addSubview(tagLbl)

        var lastAnchor = tagLbl.bottomAnchor
        var allCons: [NSLayoutConstraint] = [
            sep.topAnchor.constraint(equalTo: anchor),
            sep.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            sep.trailingAnchor.constraint(equalTo: v.trailingAnchor),
            sep.heightAnchor.constraint(equalToConstant: 1),

            section.topAnchor.constraint(equalTo: sep.bottomAnchor),
            section.leadingAnchor.constraint(equalTo: v.leadingAnchor),
            section.trailingAnchor.constraint(equalTo: v.trailingAnchor),

            tagLbl.topAnchor.constraint(equalTo: section.topAnchor, constant: 13),
            tagLbl.leadingAnchor.constraint(equalTo: section.leadingAnchor, constant: 24),
        ]

        for source in sources.prefix(6) {
            let row = NSView(); row.translatesAutoresizingMaskIntoConstraints = false
            section.addSubview(row)

            // Domain pill — warm beige + brown text
            let domLbl = makeLabel(" \(source.domain) ", size: 9, color: owlBrown, bold: true)
            domLbl.wantsLayer = true
            domLbl.layer?.backgroundColor = owlBeige.cgColor
            domLbl.layer?.cornerRadius = 4

            let titleStr = source.title.count > 58 ? String(source.title.prefix(58)) + "…" : source.title
            let titLbl = makeLabel(titleStr, size: 12, color: owlBrown)

            row.addSubview(domLbl); row.addSubview(titLbl)

            let urlStr = source.url
            let opener = URLOpener(url: urlStr)
            objc_setAssociatedObject(row, "opener_\(urlStr)", opener, .OBJC_ASSOCIATION_RETAIN)
            let tap = NSClickGestureRecognizer(target: opener, action: #selector(URLOpener.open))
            row.addGestureRecognizer(tap)
            titLbl.addGestureRecognizer(NSClickGestureRecognizer(target: opener, action: #selector(URLOpener.open)))

            allCons += [
                row.topAnchor.constraint(equalTo: lastAnchor, constant: 6),
                row.leadingAnchor.constraint(equalTo: section.leadingAnchor, constant: 24),
                row.trailingAnchor.constraint(equalTo: section.trailingAnchor, constant: -24),
                row.heightAnchor.constraint(equalToConstant: 22),

                domLbl.leadingAnchor.constraint(equalTo: row.leadingAnchor),
                domLbl.centerYAnchor.constraint(equalTo: row.centerYAnchor),

                titLbl.leadingAnchor.constraint(equalTo: domLbl.trailingAnchor, constant: 8),
                titLbl.centerYAnchor.constraint(equalTo: row.centerYAnchor),
                titLbl.trailingAnchor.constraint(lessThanOrEqualTo: row.trailingAnchor),
            ]
            lastAnchor = row.bottomAnchor
        }

        allCons.append(lastAnchor.constraint(equalTo: section.bottomAnchor, constant: -13))
        NSLayoutConstraint.activate(allCons)
        return section.bottomAnchor
    }

    private func makeFooter(timeStr: String?) -> NSView {
        let footer = NSView(); footer.wantsLayer = true
        footer.layer?.backgroundColor = owlPaper.cgColor
        footer.translatesAutoresizingMaskIntoConstraints = false

        let brand = makeLabel("🦉  STRIX", size: 12, color: owlBrown, bold: true)
        footer.addSubview(brand)

        // Close button — styled dark pill
        let closeBtn = NSButton(frame: .zero)
        closeBtn.bezelStyle = .rounded
        closeBtn.isBordered = false
        closeBtn.title = "Close"
        closeBtn.font = NSFont.systemFont(ofSize: 11, weight: .medium)
        closeBtn.contentTintColor = owlCream
        closeBtn.wantsLayer = true
        closeBtn.layer?.backgroundColor = owlBrown.cgColor
        closeBtn.layer?.cornerRadius = 7
        closeBtn.translatesAutoresizingMaskIntoConstraints = false
        closeBtn.target = self
        closeBtn.action = #selector(closeMe)
        footer.addSubview(closeBtn)

        var cons: [NSLayoutConstraint] = [
            brand.leadingAnchor.constraint(equalTo: footer.leadingAnchor, constant: 20),
            brand.centerYAnchor.constraint(equalTo: footer.centerYAnchor),

            closeBtn.trailingAnchor.constraint(equalTo: footer.trailingAnchor, constant: -16),
            closeBtn.centerYAnchor.constraint(equalTo: footer.centerYAnchor),
            closeBtn.widthAnchor.constraint(equalToConstant: 64),
            closeBtn.heightAnchor.constraint(equalToConstant: 28),
        ]

        if let t = timeStr {
            let timeLbl = makeLabel("Completed in \(t)", size: 11, color: owlMuted)
            footer.addSubview(timeLbl)
            cons += [
                timeLbl.centerXAnchor.constraint(equalTo: footer.centerXAnchor),
                timeLbl.centerYAnchor.constraint(equalTo: footer.centerYAnchor),
            ]
        }

        NSLayoutConstraint.activate(cons)
        return footer
    }

    private func makeSep() -> NSView {
        let v = NSView(); v.wantsLayer = true
        v.layer?.backgroundColor = owlBeige.cgColor
        v.translatesAutoresizingMaskIntoConstraints = false
        return v
    }

    private func makeLabel(_ text: String, size: CGFloat, color: NSColor,
                           bold: Bool = false, italic: Bool = false,
                           wrap: CGFloat = 0) -> NSTextField {
        let font: NSFont
        if bold {
            font = NSFont.boldSystemFont(ofSize: size)
        } else if italic {
            font = NSFontManager.shared.font(
                withFamily: "SF Pro Text", traits: .italicFontMask,
                weight: 5, size: size
            ) ?? NSFont.systemFont(ofSize: size)
        } else {
            font = NSFont.systemFont(ofSize: size)
        }

        let lbl: NSTextField
        if wrap > 0 {
            lbl = NSTextField(wrappingLabelWithString: text)
            lbl.preferredMaxLayoutWidth = wrap
        } else {
            lbl = NSTextField(labelWithString: text)
        }
        lbl.font = font
        lbl.textColor = color
        lbl.translatesAutoresizingMaskIntoConstraints = false
        return lbl
    }

    private func sizeWindow() {
        contentView?.layoutSubtreeIfNeeded()
        if let size = contentView?.fittingSize {
            setContentSize(NSSize(width: max(size.width, 380), height: max(size.height, 140)))
        }
        center()
    }
}


// MARK: - URL Opener helper

class URLOpener: NSObject {
    let urlString: String
    init(url: String) { self.urlString = url }
    @objc func open() {
        if let url = URL(string: urlString) { NSWorkspace.shared.open(url) }
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    var hotKeyRef: EventHotKeyRef?

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.setActivationPolicy(.accessory)
        setupMenuBar()
        registerHotKey()
        print("STRIX Helper running — Cmd+Shift+X")
    }

    func setupMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem?.button?.title = "🦉"

        let menu = NSMenu()
        let items: [(String, Selector?)] = [
            ("Check Selected Text  ⌘⇧X", #selector(triggerCheck)),
            ("-", nil),
            ("Open Dashboard", #selector(openDashboard)),
            ("-", nil),
            ("Quit STRIX", #selector(quitApp)),
        ]
        for (title, action) in items {
            if title == "-" { menu.addItem(.separator()) }
            else {
                let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
                item.target = self
                menu.addItem(item)
            }
        }
        statusItem?.menu = menu
    }

    func registerHotKey() {
        var id = EventHotKeyID()
        id.signature = 0x53545258  // "STRX"
        id.id = 1
        RegisterEventHotKey(7, UInt32(cmdKey | shiftKey), id, GetApplicationEventTarget(), 0, &hotKeyRef)

        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        var ref: EventHandlerRef? = nil
        InstallEventHandler(GetApplicationEventTarget(), { _, _, userData -> OSStatus in
            guard let ud = userData else { return OSStatus(noErr) }
            let d = Unmanaged<AppDelegate>.fromOpaque(ud).takeUnretainedValue()
            DispatchQueue.main.async { d.triggerCheck() }
            return OSStatus(noErr)
        }, 1, &spec, Unmanaged.passUnretained(self).toOpaque(), &ref)
    }

    @objc func triggerCheck() {
        DispatchQueue.global().async {
            Thread.sleep(forTimeInterval: 0.1)
            let src = CGEventSource(stateID: .hidSystemState)
            let dn = CGEvent(keyboardEventSource: src, virtualKey: 0x08, keyDown: true)!
            dn.flags = .maskCommand; dn.post(tap: .cgSessionEventTap)
            let up = CGEvent(keyboardEventSource: src, virtualKey: 0x08, keyDown: false)!
            up.flags = .maskCommand; up.post(tap: .cgSessionEventTap)
            Thread.sleep(forTimeInterval: 0.35)

            let text = NSPasteboard.general
                .string(forType: .string)?
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""

            guard !text.isEmpty else {
                StrixPopup.showError("No text selected.\nSelect some text first, then press ⌘⇧X.")
                return
            }

            StrixPopup.showLoading(claim: text)
            self.callBackend(text: text)
        }
    }

    func callBackend(text: String) {
        guard let url = URL(string: "http://127.0.0.1:8000/api/check") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 120
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["text": text])

        URLSession.shared.dataTask(with: req) { data, _, error in
            if let error = error {
                let nsError = error as NSError
                if nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorTimedOut {
                    StrixPopup.showError("Analysis timed out after 120s.\nBackend is running, but this check took too long.")
                } else {
                    StrixPopup.showError("Backend not reachable.\n\(error.localizedDescription)")
                }
                return
            }
            guard let data = data else {
                StrixPopup.showError("No response from backend.")
                return
            }
            do {
                let verdict = try JSONDecoder().decode(Verdict.self, from: data)
                StrixPopup.show(verdict: verdict)
            } catch {
                StrixPopup.showError("Could not parse response:\n\(error.localizedDescription)")
            }
        }.resume()
    }

    @objc func openDashboard() { NSWorkspace.shared.open(URL(string: "http://localhost:5173")!) }
    @objc func quitApp()       { NSApp.terminate(nil) }
}

// MARK: - Entry Point

let app      = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
