/**
 * generateCounsellingPdf.js
 * =========================
 * Client-side PDF generation utility for the Heart Health Counselling & Education Guide.
 * 
 * Generates a standard, fully compliant PDF (ISO 32000-1 / PDF 1.4) containing
 * all six clinical counselling domains (Categories A through F) with their complete
 * counselling points, clinical explanations, practical tips, and pagination metadata.
 * 
 * Features:
 * - 100% pure JavaScript: Zero third-party npm dependencies required.
 * - Standard Type 1 Helvetica fonts with WinAnsiEncoding.
 * - Dynamic two-pass page numbering ("Page X of Y").
 * - Clean medical typography, colored domain headers, and structured tip callout boxes.
 * - Full character sanitization for clinical symbols (quotations, dashes, >=, <=).
 */

function sanitizeForPdf(text) {
  if (!text) return ''
  return String(text)
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2013\u2014]/g, '-')
    .replace(/\u2022/g, '*')
    .replace(/\u2265/g, '>=')
    .replace(/\u2264/g, '<=')
    .replace(/[\u00A0]/g, ' ')
    .replace(/[^\x20-\x7E\n\r\t]/g, '')
}

function wrapWords(text, maxChars = 92) {
  if (!text) return []
  const words = text.split(/\s+/)
  const lines = []
  let cur = ''

  for (const w of words) {
    if (!cur) {
      cur = w
    } else if (cur.length + 1 + w.length <= maxChars) {
      cur += ' ' + w
    } else {
      lines.push(cur)
      cur = w
    }
  }
  if (cur) lines.push(cur)
  return lines
}

export function generateCounsellingGuidePdf(categories) {
  const pageWidth = 595.28 // A4 width in pt
  const pageHeight = 841.89 // A4 height in pt
  const leftMargin = 40
  const rightMargin = 40
  const contentWidth = pageWidth - leftMargin - rightMargin // 515.28 pt
  const topMargin = 44
  const bottomMargin = 45

  const pages = []
  let curCommands = []

  function newPage() {
    curCommands = []
    pages.push(curCommands)
  }

  function addRaw(cmd) {
    curCommands.push(cmd)
  }

  function drawRect(x, y, w, h, fillColor = null, strokeColor = null, lineWidth = 1) {
    const py = pageHeight - y - h
    let s = 'q\n'
    if (lineWidth) s += `${lineWidth} w\n`
    if (fillColor) s += `${fillColor[0].toFixed(3)} ${fillColor[1].toFixed(3)} ${fillColor[2].toFixed(3)} rg\n`
    if (strokeColor) s += `${strokeColor[0].toFixed(3)} ${strokeColor[1].toFixed(3)} ${strokeColor[2].toFixed(3)} RG\n`
    s += `${x.toFixed(2)} ${py.toFixed(2)} ${w.toFixed(2)} ${h.toFixed(2)} re\n`
    if (fillColor && strokeColor) s += 'B\n'
    else if (fillColor) s += 'f\n'
    else if (strokeColor) s += 'S\n'
    s += 'Q\n'
    addRaw(s)
  }

  function drawLine(x1, y1, x2, y2, strokeColor = [0.85, 0.88, 0.92], lineWidth = 0.75) {
    const py1 = pageHeight - y1
    const py2 = pageHeight - y2
    let s = 'q\n'
    s += `${lineWidth} w\n`
    s += `${strokeColor[0].toFixed(3)} ${strokeColor[1].toFixed(3)} ${strokeColor[2].toFixed(3)} RG\n`
    s += `${x1.toFixed(2)} ${py1.toFixed(2)} m ${x2.toFixed(2)} ${py2.toFixed(2)} l S\n`
    s += 'Q\n'
    addRaw(s)
  }

  function drawText(str, x, y, options = {}) {
    const font = options.font || 'F1'
    const size = options.size || 10
    const color = options.color || [0.1, 0.1, 0.1]
    const py = pageHeight - y
    const safe = sanitizeForPdf(str)

    let s = 'BT\n'
    s += `/${font} ${size} Tf\n`
    s += `${color[0].toFixed(3)} ${color[1].toFixed(3)} ${color[2].toFixed(3)} rg\n`
    s += `${x.toFixed(2)} ${py.toFixed(2)} Td\n`
    s += `(${safe}) Tj\n`
    s += 'ET\n'
    addRaw(s)
  }

  // Domain RGB color mappings
  const colorMap = {
    A: [0.086, 0.639, 0.290], // Green
    B: [0.145, 0.388, 0.922], // Blue
    C: [0.486, 0.227, 0.929], // Purple
    D: [0.051, 0.580, 0.533], // Teal
    E: [0.918, 0.345, 0.047], // Orange
    F: [0.008, 0.518, 0.780], // Sky Blue
  }

  // 1. Initialize First Page
  newPage()
  let currentY = topMargin

  // Header Hero Banner on Page 1
  drawRect(leftMargin, currentY, contentWidth, 72, [0.043, 0.122, 0.227], null) // Navy #0B1F3A
  drawText('CARDIOPREDICT CLINICAL AI - DECISION SUPPORT PLATFORM', leftMargin + 16, currentY + 18, {
    font: 'F2',
    size: 7.5,
    color: [0.22, 0.74, 0.97], // #38BDF8
  })
  drawText('Heart Health Counselling & Education Guide', leftMargin + 16, currentY + 38, {
    font: 'F2',
    size: 15,
    color: [1, 1, 1],
  })
  drawText('Evidence-based patient counselling framework across six core lifestyle domains (Categories A through F).', leftMargin + 16, currentY + 54, {
    font: 'F1',
    size: 8.5,
    color: [0.86, 0.92, 0.99],
  })

  currentY += 84

  // 2. Iterate through all six categories
  for (let cIdx = 0; cIdx < categories.length; cIdx++) {
    const cat = categories[cIdx]
    const accentRgb = colorMap[cat.code] || [0.145, 0.388, 0.922]

    // Verify minimum required vertical space for Category Header + at least 1 point
    if (currentY + 115 > pageHeight - bottomMargin) {
      newPage()
      currentY = topMargin + 15
    }

    // Category Header Box
    drawRect(leftMargin, currentY, contentWidth, 34, [0.97, 0.98, 0.99], [0.85, 0.88, 0.92], 1)
    drawRect(leftMargin, currentY, 4, 34, accentRgb, null) // Left accent bar

    drawText(`Category ${cat.code}: ${cat.title}`, leftMargin + 12, currentY + 14, {
      font: 'F2',
      size: 11,
      color: [0.043, 0.122, 0.227],
    })
    drawText(cat.tagline || '', leftMargin + 12, currentY + 26, {
      font: 'F3',
      size: 7.5,
      color: [0.39, 0.45, 0.55],
    })

    currentY += 42

    // Render Counselling Points
    const points = cat.counsellingPoints || []
    for (let pIdx = 0; pIdx < points.length; pIdx++) {
      const point = points[pIdx]
      const expLines = wrapWords(point.explanation, 92)
      const tipLines = wrapWords(point.counsellingTip, 88)

      const expHeight = expLines.length * 11
      const tipBoxHeight = tipLines.length * 10 + 16
      const totalPointHeight = 16 + expHeight + 6 + tipBoxHeight + 10

      // Auto-paginate if point overflows bottom margin
      if (currentY + totalPointHeight > pageHeight - bottomMargin) {
        newPage()
        currentY = topMargin + 15
      }

      // Point Title
      drawText(`${pIdx + 1}.  ${point.title}`, leftMargin + 4, currentY + 10, {
        font: 'F2',
        size: 9.5,
        color: [0.043, 0.122, 0.227],
      })
      currentY += 15

      // Explanation lines
      for (const line of expLines) {
        drawText(line, leftMargin + 14, currentY + 8, {
          font: 'F1',
          size: 8.5,
          color: [0.2, 0.25, 0.33],
        })
        currentY += 11
      }
      currentY += 3

      // Practical Counselling Tip Callout Card
      drawRect(leftMargin + 14, currentY, contentWidth - 14, tipBoxHeight, [0.97, 0.98, 0.99], [0.90, 0.92, 0.95], 0.5)
      drawRect(leftMargin + 14, currentY, 3, tipBoxHeight, accentRgb, null)

      drawText('Clinical Counselling Tip:', leftMargin + 22, currentY + 10, {
        font: 'F2',
        size: 7.5,
        color: [0.25, 0.35, 0.45],
      })

      let tipY = currentY + 20
      for (const line of tipLines) {
        drawText(line, leftMargin + 22, tipY, {
          font: 'F3',
          size: 8,
          color: [0.15, 0.25, 0.35],
        })
        tipY += 10
      }

      currentY += tipBoxHeight + 8
    }

    currentY += 8
  }

  // 3. Second Pass: Add running headers & footers with exact total page count
  const totalPages = pages.length
  for (let p = 0; p < totalPages; p++) {
    curCommands = pages[p]

    // Running Header on pages 2+
    if (p > 0) {
      drawLine(leftMargin, topMargin - 8, leftMargin + contentWidth, topMargin - 8, [0.85, 0.88, 0.92], 0.5)
      drawText('CardioPredict Clinical AI  |  Heart Health Counselling & Education Guide', leftMargin, topMargin - 14, {
        font: 'F2',
        size: 7.5,
        color: [0.4, 0.45, 0.55],
      })
      drawText('Complete Categories A through F', leftMargin + contentWidth - 135, topMargin - 14, {
        font: 'F1',
        size: 7.5,
        color: [0.55, 0.6, 0.7],
      })
    }

    // Running Footer on all pages
    const footerY = pageHeight - bottomMargin + 18
    drawLine(leftMargin, footerY - 8, leftMargin + contentWidth, footerY - 8, [0.85, 0.88, 0.92], 0.5)
    drawText('Guideline-Directed Medical Education - Professional Healthcare Consultation Reference', leftMargin, footerY + 2, {
      font: 'F1',
      size: 7,
      color: [0.5, 0.55, 0.65],
    })
    drawText(`Page ${p + 1} of ${totalPages}`, leftMargin + contentWidth - 55, footerY + 2, {
      font: 'F2',
      size: 7.5,
      color: [0.3, 0.35, 0.45],
    })
  }

  // 4. Assemble PDF Object Tree & Cross-Reference Table
  let out = '%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'
  const offsets = []
  let nextId = 1

  const catalogId = nextId++
  const pagesId = nextId++
  const fontRegId = nextId++
  const fontBoldId = nextId++
  const fontObliqueId = nextId++

  const pageObjIds = []
  const contentObjIds = []

  for (let i = 0; i < totalPages; i++) {
    pageObjIds.push(nextId++)
    contentObjIds.push(nextId++)
  }

  const objects = []
  objects[catalogId] = `<< /Type /Catalog /Pages ${pagesId} 0 R >>`
  const kidsStr = pageObjIds.map((id) => `${id} 0 R`).join(' ')
  objects[pagesId] = `<< /Type /Pages /Kids [${kidsStr}] /Count ${totalPages} >>`

  // Standard 14 Type 1 Fonts with WinAnsiEncoding
  objects[fontRegId] = `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>`
  objects[fontBoldId] = `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>`
  objects[fontObliqueId] = `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>`

  for (let i = 0; i < totalPages; i++) {
    const pId = pageObjIds[i]
    const cId = contentObjIds[i]
    const pageStream = pages[i].join('')
    const streamLen = new TextEncoder().encode(pageStream).length

    objects[pId] = `<< /Type /Page /Parent ${pagesId} 0 R /MediaBox [0 0 ${pageWidth.toFixed(2)} ${pageHeight.toFixed(2)}] /Resources << /Font << /F1 ${fontRegId} 0 R /F2 ${fontBoldId} 0 R /F3 ${fontObliqueId} 0 R >> >> /Contents ${cId} 0 R >>`
    objects[cId] = `<< /Length ${streamLen} >>\nstream\n${pageStream}\nendstream`
  }

  for (let i = 1; i < nextId; i++) {
    offsets[i] = new TextEncoder().encode(out).length
    out += `${i} 0 obj\n${objects[i]}\nendobj\n`
  }

  const startXref = new TextEncoder().encode(out).length
  out += `xref\n0 ${nextId}\n0000000000 65535 f \n`
  for (let i = 1; i < nextId; i++) {
    const off = String(offsets[i]).padStart(10, '0')
    out += `${off} 00000 n \n`
  }

  out += `trailer\n<< /Size ${nextId} /Root ${catalogId} 0 R >>\nstartxref\n${startXref}\n%%EOF\n`

  // 5. Trigger download in browser
  const blob = new Blob([new TextEncoder().encode(out)], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'Heart_Health_Counselling_and_Education_Guide.pdf'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
