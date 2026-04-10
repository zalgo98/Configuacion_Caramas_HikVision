param(
    [string]$Ip,
    [string]$User,
    [string]$Password,
    [string]$Track
)

$ErrorActionPreference = "Stop"

$baseUrl = "http://$Ip"
$tmpIn  = Join-Path $env:TEMP "track_${Ip}_$Track.xml"
$tmpOut = Join-Path $env:TEMP "track_${Ip}_${Track}_mod.xml"

$resp = curl.exe -s -o $tmpIn -w "%{http_code}" --digest -u "${User}:${Password}" "$baseUrl/ISAPI/ContentMgmt/record/tracks/$Track"
if ($resp -ne "200") {
    Write-Output "ERROR leyendo track $Track HTTP $resp"
    exit 1
}

$xml = New-Object System.Xml.XmlDocument
$xml.PreserveWhitespace = $true
$xml.Load($tmpIn)

$nsUri = $xml.DocumentElement.NamespaceURI
$ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace("n", $nsUri)

$days = "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
$actions = @($xml.SelectNodes("//n:TrackSchedule//n:ScheduleAction", $ns))
$changed = $false

# activar enableSchedule
$enableScheduleNodes = $xml.SelectNodes("//*[local-name()='enableSchedule']")
foreach ($n in $enableScheduleNodes) {
    if ($n.InnerText -ne "true") {
        $n.InnerText = "true"
        $changed = $true
    }
}

if ($actions.Count -lt 1) {
    $block = $xml.SelectSingleNode("//n:TrackSchedule//n:ScheduleBlock", $ns)
    if ($block -eq $null) {
        Write-Output "ERROR track $Track no tiene ScheduleBlock"
        exit 2
    }

    $id = 1
    foreach ($day in $days) {
        $a = $xml.CreateElement("ScheduleAction", $nsUri)

        $n1 = $xml.CreateElement("id", $nsUri)
        $n1.InnerText = [string]$id
        $a.AppendChild($n1) > $null

        $sst = $xml.CreateElement("ScheduleActionStartTime", $nsUri)
        $sd = $xml.CreateElement("DayOfWeek", $nsUri)
        $sd.InnerText = $day
        $sst.AppendChild($sd) > $null
        $st = $xml.CreateElement("TimeOfDay", $nsUri)
        $st.InnerText = "00:00:00"
        $sst.AppendChild($st) > $null
        $a.AppendChild($sst) > $null

        $set = $xml.CreateElement("ScheduleActionEndTime", $nsUri)
        $ed = $xml.CreateElement("DayOfWeek", $nsUri)
        $ed.InnerText = $day
        $set.AppendChild($ed) > $null
        $et = $xml.CreateElement("TimeOfDay", $nsUri)
        $et.InnerText = "24:00:00"
        $set.AppendChild($et) > $null
        $a.AppendChild($set) > $null

        $dst = $xml.CreateElement("ScheduleDSTEnable", $nsUri)
        $dst.InnerText = "false"
        $a.AppendChild($dst) > $null

        $desc = $xml.CreateElement("Description", $nsUri)
        $desc.InnerText = "nothing"
        $a.AppendChild($desc) > $null

        $acts = $xml.CreateElement("Actions", $nsUri)
        $rec = $xml.CreateElement("Record", $nsUri)
        $rec.InnerText = "true"
        $acts.AppendChild($rec) > $null
        $mode = $xml.CreateElement("ActionRecordingMode", $nsUri)
        $mode.InnerText = "CMR"
        $acts.AppendChild($mode) > $null
        $a.AppendChild($acts) > $null

        $block.AppendChild($a) > $null
        $id++
    }
    $changed = $true
}
else {
    $existing = @{}
    foreach ($a in $actions) {
        $d = $a.SelectSingleNode("n:ScheduleActionStartTime/n:DayOfWeek", $ns)
        if ($d -ne $null) { $existing[$d.InnerText] = $a }
    }

    $template = $actions[0]
    $parent = $template.ParentNode

    foreach ($day in $days) {
        if ($existing.ContainsKey($day)) {
            $a = $existing[$day]
        } else {
            $a = $template.CloneNode($true)
            $idNode = $a.SelectSingleNode("n:id", $ns)
            if ($idNode -ne $null) {
                $idNode.InnerText = [string]($parent.SelectNodes("n:ScheduleAction", $ns).Count + 1)
            }
            $parent.AppendChild($a) > $null
            $changed = $true
        }

        $sd = $a.SelectSingleNode("n:ScheduleActionStartTime/n:DayOfWeek", $ns)
        if ($sd -ne $null -and $sd.InnerText -ne $day) { $sd.InnerText = $day; $changed = $true }

        $st = $a.SelectSingleNode("n:ScheduleActionStartTime/n:TimeOfDay", $ns)
        if ($st -ne $null -and $st.InnerText -ne "00:00:00") { $st.InnerText = "00:00:00"; $changed = $true }

        $ed = $a.SelectSingleNode("n:ScheduleActionEndTime/n:DayOfWeek", $ns)
        if ($ed -ne $null -and $ed.InnerText -ne $day) { $ed.InnerText = $day; $changed = $true }

        $et = $a.SelectSingleNode("n:ScheduleActionEndTime/n:TimeOfDay", $ns)
        if ($et -ne $null -and $et.InnerText -ne "24:00:00") { $et.InnerText = "24:00:00"; $changed = $true }

        $dst = $a.SelectSingleNode("n:ScheduleDSTEnable", $ns)
        if ($dst -ne $null -and $dst.InnerText -ne "false") { $dst.InnerText = "false"; $changed = $true }

        $desc = $a.SelectSingleNode("n:Description", $ns)
        if ($desc -ne $null -and $desc.InnerText -ne "nothing") { $desc.InnerText = "nothing"; $changed = $true }

        $rec = $a.SelectSingleNode("n:Actions/n:Record", $ns)
        if ($rec -ne $null -and $rec.InnerText -ne "true") { $rec.InnerText = "true"; $changed = $true }

        $mode = $a.SelectSingleNode("n:Actions/n:ActionRecordingMode", $ns)
        if ($mode -ne $null -and $mode.InnerText -ne "CMR") { $mode.InnerText = "CMR"; $changed = $true }
    }
}

# corregir ScheduleActionSize
$blockNode = $xml.SelectSingleNode("//n:TrackSchedule//n:ScheduleBlock", $ns)
if ($blockNode -ne $null -and $blockNode.Attributes["ScheduleActionSize"] -ne $null) {
    $realCount = $blockNode.SelectNodes("n:ScheduleAction", $ns).Count
    if ($blockNode.Attributes["ScheduleActionSize"].Value -ne [string]$realCount) {
        $blockNode.Attributes["ScheduleActionSize"].Value = [string]$realCount
        $changed = $true
    }
}

if (-not $changed) {
    Write-Output "OK horario ya correcto $Track"
    exit 0
}

$xml.Save($tmpOut)

$putResp = curl.exe -s -o nul -w "%{http_code}" --digest -u "${User}:${Password}" -X PUT -H "Content-Type: application/xml" --data-binary "@$tmpOut" "$baseUrl/ISAPI/ContentMgmt/record/tracks/$Track"
if ($putResp -notin @("200","201")) {
    Write-Output "ERROR cambiando horario en track $Track HTTP $putResp"
    exit 3
}

Write-Output "OK horario aplicado $Track"
exit 0