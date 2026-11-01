// Regenerate the website's favicon assets from the unmodified app artwork.
// Usage: swift -disable-sandbox scripts/export_favicons.swift [site-root]
import AppKit

let root = URL(fileURLWithPath: CommandLine.arguments.dropFirst().first ?? FileManager.default.currentDirectoryPath)
let brand = root.appendingPathComponent("assets/brand", isDirectory: true)
let source = NSImage(contentsOf: root.appendingPathComponent("assets/press/kit/atlasdays-icon.png"))!
// Match the brand mark's 7.385px corners at 32px, with a white/12% hairline.
// The app artwork, its background and composition stay intact.
let cornerRatio: CGFloat = 7.385 / 32

func bitmap(_ size: Int) -> NSBitmapImageRep {
    NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
}

func render(_ size: Int, circular: Bool = false) -> Data {
    let master = bitmap(1024)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: master)
    NSGraphicsContext.current!.imageInterpolation = .high
    let bounds = NSRect(x: 0, y: 0, width: 1024, height: 1024)
    let radius: CGFloat = circular ? 512 : 1024 * cornerRatio
    let clip = NSBezierPath(roundedRect: bounds, xRadius: radius, yRadius: radius)
    clip.addClip()
    source.draw(in: bounds)
    // Half a pixel at tab sizes, at most one pixel in larger exports.
    let border = min(1, max(0.5, CGFloat(size) / 192)) * 1024 / CGFloat(size)
    let outline = NSBezierPath(roundedRect: bounds.insetBy(dx: border / 2, dy: border / 2),
        xRadius: radius - border / 2, yRadius: radius - border / 2)
    outline.lineWidth = border
    NSColor.white.withAlphaComponent(0.12).setStroke()
    outline.stroke()
    NSGraphicsContext.restoreGraphicsState()

    let output = bitmap(size)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: output)
    NSGraphicsContext.current!.imageInterpolation = .high
    NSImage(cgImage: master.cgImage!, size: NSSize(width: 1024, height: 1024))
        .draw(in: NSRect(x: 0, y: 0, width: size, height: size))
    NSGraphicsContext.restoreGraphicsState()
    precondition(output.colorAt(x: 0, y: 0)!.alphaComponent < 0.01)
    precondition(output.colorAt(x: size / 2, y: size / 2)!.alphaComponent > 0.99)
    return output.representation(using: .png, properties: [:])!
}

try render(192).write(to: brand.appendingPathComponent("favicon.png"))
try render(192, circular: true).write(to: brand.appendingPathComponent("favicon-round.png"))
try render(180).write(to: brand.appendingPathComponent("apple-touch-icon.png"))

// A scalable wrapper preserves the exact rounded outline in browser tabs.
// The embedded image is the original artwork, without a second baked mask.
let embedded = bitmap(256)
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: embedded)
NSGraphicsContext.current!.imageInterpolation = .high
source.draw(in: NSRect(x: 0, y: 0, width: 256, height: 256))
NSGraphicsContext.restoreGraphicsState()
let imageData = embedded.representation(using: .png, properties: [:])!.base64EncodedString()
let svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>AtlasDays</title>
  <defs><clipPath id="corners"><rect width="256" height="256" rx="59.08"/></clipPath></defs>
  <image width="256" height="256" clip-path="url(#corners)" href="data:image/png;base64,\(imageData)"/>
  <rect x="0.25" y="0.25" width="255.5" height="255.5" rx="58.83" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width=".5" vector-effect="non-scaling-stroke"/>
</svg>

"""
try svg.write(to: brand.appendingPathComponent("favicon.svg"), atomically: true, encoding: .utf8)

// PNG-backed ICO frames provide the same rounded mark to older clients and
// to browsers that automatically request the conventional root favicon URL.
let sizes = [16, 32, 48]
let frames = sizes.map { render($0) }
var ico = Data()
func word(_ value: UInt16) { ico.append(UInt8(value & 255)); ico.append(UInt8(value >> 8)) }
func dword(_ value: UInt32) {
    for shift in stride(from: 0, to: 32, by: 8) { ico.append(UInt8((value >> shift) & 255)) }
}
word(0); word(1); word(UInt16(sizes.count))
var offset = UInt32(6 + 16 * sizes.count)
for (size, frame) in zip(sizes, frames) {
    ico.append(contentsOf: [UInt8(size), UInt8(size), 0, 0])
    word(1); word(32); dword(UInt32(frame.count)); dword(offset)
    offset += UInt32(frame.count)
}
for frame in frames { ico.append(frame) }
try ico.write(to: root.appendingPathComponent("favicon.ico"))
print("Exported rounded SVG, 192px PNG, 180px touch icon, 16/32/48px ICO and circular 192px PNG.")
