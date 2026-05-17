param(
    [string]$Title = "Codex is waiting",
    [string]$Message = "Click Continue when you are ready.",
    [string]$ContinueText = "Continue",
    [string]$CancelText = "Cancel",
    [int]$TimeoutSeconds = 0,
    [switch]$NoCancel
)

$ErrorActionPreference = "Stop"
$started = Get-Date

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    [System.Windows.Forms.Application]::EnableVisualStyles()
    [System.Media.SystemSounds]::Asterisk.Play()

    $form = New-Object System.Windows.Forms.Form
    $form.Text = $Title
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
    $form.TopMost = $true
    $form.ShowInTaskbar = $true
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.ClientSize = New-Object System.Drawing.Size(560, 230)

    $font = New-Object System.Drawing.Font("Microsoft YaHei UI", 11)

    $label = New-Object System.Windows.Forms.Label
    $label.Font = $font
    $label.Text = $Message
    $label.AutoSize = $false
    $label.Location = New-Object System.Drawing.Point(24, 22)
    $label.Size = New-Object System.Drawing.Size(512, 116)
    $label.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
    $form.Controls.Add($label)

    $status = New-Object System.Windows.Forms.Label
    $status.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 9)
    $status.ForeColor = [System.Drawing.Color]::DimGray
    $status.AutoSize = $false
    $status.Location = New-Object System.Drawing.Point(24, 144)
    $status.Size = New-Object System.Drawing.Size(512, 24)
    if ($TimeoutSeconds -gt 0) {
        $status.Text = "Timeout in $TimeoutSeconds seconds."
    } else {
        $status.Text = "Waiting for user confirmation."
    }
    $form.Controls.Add($status)

    $okButton = New-Object System.Windows.Forms.Button
    $okButton.Text = $ContinueText
    $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $okButton.Size = New-Object System.Drawing.Size(128, 36)
    $okButton.Location = New-Object System.Drawing.Point(276, 180)
    $form.Controls.Add($okButton)
    $form.AcceptButton = $okButton

    if (-not $NoCancel) {
        $cancelButton = New-Object System.Windows.Forms.Button
        $cancelButton.Text = $CancelText
        $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
        $cancelButton.Size = New-Object System.Drawing.Size(128, 36)
        $cancelButton.Location = New-Object System.Drawing.Point(414, 180)
        $form.Controls.Add($cancelButton)
        $form.CancelButton = $cancelButton
    }

    $timedOut = $false
    $timer = $null
    $deadline = $null
    if ($TimeoutSeconds -gt 0) {
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 250
        $timer.Add_Tick({
            $remaining = [Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)
            if ($remaining -le 0) {
                $script:timedOut = $true
                $timer.Stop()
                $form.DialogResult = [System.Windows.Forms.DialogResult]::Abort
                $form.Close()
            } else {
                $status.Text = "Timeout in $remaining seconds."
            }
        })
        $timer.Start()
    }

    $form.Add_Shown({
        $form.Activate()
        $form.BringToFront()
        $form.Focus()
    })

    $dialogResult = $form.ShowDialog()
    if ($timer -ne $null) {
        $timer.Stop()
        $timer.Dispose()
    }

    $result = "closed"
    $exitCode = 4
    if ($dialogResult -eq [System.Windows.Forms.DialogResult]::OK) {
        $result = "continue"
        $exitCode = 0
    } elseif ($dialogResult -eq [System.Windows.Forms.DialogResult]::Cancel) {
        $result = "cancel"
        $exitCode = 2
    } elseif ($dialogResult -eq [System.Windows.Forms.DialogResult]::Abort -or $timedOut) {
        $result = "timeout"
        $exitCode = 3
    }

    $ended = Get-Date
    [ordered]@{
        ok = ($result -eq "continue")
        result = $result
        title = $Title
        timeout_seconds = $TimeoutSeconds
        started_at_utc = $started.ToUniversalTime().ToString("o")
        ended_at_utc = $ended.ToUniversalTime().ToString("o")
        elapsed_s = [Math]::Round(($ended - $started).TotalSeconds, 3)
    } | ConvertTo-Json -Depth 3

    exit $exitCode
} catch {
    $ended = Get-Date
    [ordered]@{
        ok = $false
        result = "error"
        title = $Title
        error = $_.Exception.Message
        started_at_utc = $started.ToUniversalTime().ToString("o")
        ended_at_utc = $ended.ToUniversalTime().ToString("o")
        elapsed_s = [Math]::Round(($ended - $started).TotalSeconds, 3)
    } | ConvertTo-Json -Depth 3
    exit 5
}
