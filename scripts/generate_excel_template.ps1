$ErrorActionPreference = "Stop"

function Write-Utf8File {
    param(
        [string]$Path,
        [string]$Content
    )

    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.Encoding]::UTF8)
}

$root = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $root "data"
$templateDir = Join-Path $env:TEMP ("jobs-xlsx-" + [guid]::NewGuid().ToString())

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
New-Item -ItemType Directory -Force -Path $templateDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $templateDir "_rels") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $templateDir "xl") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $templateDir "xl\_rels") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $templateDir "xl\worksheets") | Out-Null

$columns = @(
    "&#x62DB;&#x8058;&#x7F51;&#x7AD9;",
    "&#x5C97;&#x4F4D;&#x540D;&#x79F0;",
    "&#x516C;&#x53F8;&#x540D;&#x79F0;",
    "&#x85AA;&#x8D44;",
    "&#x5DE5;&#x4F5C;&#x5730;&#x70B9;",
    "&#x5B66;&#x5386;",
    "&#x7ECF;&#x9A8C;",
    "&#x878D;&#x8D44;&#x60C5;&#x51B5;",
    "&#x516C;&#x53F8;&#x89C4;&#x6A21;",
    "&#x884C;&#x4E1A;",
    "&#x798F;&#x5229;&#x5F85;&#x9047;",
    "&#x53D1;&#x5E03;&#x65E5;&#x671F;",
    "&#x8BE6;&#x60C5;&#x9875;",
    "&#x6280;&#x80FD;&#x8981;&#x6C42;"
)

$letters = @("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N")
$rowCells = for ($i = 0; $i -lt $columns.Count; $i++) {
    '<c r="' + $letters[$i] + '1" t="inlineStr"><is><t>' + $columns[$i] + "</t></is></c>"
}
$sheetRows = $rowCells -join ""

Write-Utf8File -Path (Join-Path $templateDir "[Content_Types].xml") -Content @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
'@

Write-Utf8File -Path (Join-Path $templateDir "_rels\.rels") -Content @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
'@

Write-Utf8File -Path (Join-Path $templateDir "xl\workbook.xml") -Content @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Jobs" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
'@

Write-Utf8File -Path (Join-Path $templateDir "xl\_rels\workbook.xml.rels") -Content @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
'@

Write-Utf8File -Path (Join-Path $templateDir "xl\styles.xml") -Content @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>
'@

$sheetXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">$sheetRows</row>
  </sheetData>
</worksheet>
"@

Write-Utf8File -Path (Join-Path $templateDir "xl\worksheets\sheet1.xml") -Content $sheetXml

$xlsxPath = Join-Path $dataDir "jobs.xlsx"
if (Test-Path $xlsxPath) {
    Remove-Item $xlsxPath -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($templateDir, $xlsxPath)

Remove-Item $templateDir -Recurse -Force
Write-Output $xlsxPath
