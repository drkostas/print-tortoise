// qrender.swift — render each page of a PDF with Apple's own PDF engine (CoreGraphics, the one
// Preview and Quick Look use) to PNG files: qrender <file.pdf> <prefix> <dpi>, writing
// <prefix>-p1.png, <prefix>-p2.png ....
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 4, let dpi = Double(args[3]) else {
    FileHandle.standardError.write("usage: qrender <file.pdf> <prefix> <dpi>\n".data(using: .utf8)!)
    exit(2)
}
let url = URL(fileURLWithPath: args[1])
guard let doc = CGPDFDocument(url as CFURL), doc.numberOfPages > 0 else {
    FileHandle.standardError.write("cannot open \(args[1]) as a PDF\n".data(using: .utf8)!)
    exit(1)
}
for i in 1...doc.numberOfPages {
    let page = doc.page(at: i)!
    let box = page.getBoxRect(.mediaBox)
    let scale = dpi / 72.0
    let w = Int((box.width * scale).rounded()), h = Int((box.height * scale).rounded())
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -box.origin.x, y: -box.origin.y)
    ctx.drawPDFPage(page)
    let out = URL(fileURLWithPath: "\(args[2])-p\(i).png")
    let dest = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
    print(out.path)
}
