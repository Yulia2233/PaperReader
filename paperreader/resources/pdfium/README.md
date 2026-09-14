# PDFium runtime libraries

The viewer uses `pdfium-render` and looks for the platform library in this directory or in `PAPERREADER_PDFIUM_DIR` before trying the system library.

Expected names:

- macOS: `libpdfium.dylib`
- Linux: `libpdfium.so`
- Windows: `pdfium.dll`

Release bundles should place the matching library beside the executable under `resources/pdfium`. Download a build matching the target architecture from the [official PDFium binaries](https://github.com/bblanchon/pdfium-binaries/releases), then run:

```text
PAPERREADER_PDFIUM_DIR=/path/to/pdfium cargo run -- path/to/paper
```

The library is intentionally not committed to the source repository because it is platform-specific and large.
