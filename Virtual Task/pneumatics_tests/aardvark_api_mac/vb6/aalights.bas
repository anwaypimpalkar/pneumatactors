Attribute VB_Name = "aalights"
'==========================================================================
' (c) 2004  Total Phase, Inc.
'--------------------------------------------------------------------------
' Project : Aardvark Sample Code
' File    : aalights.bas
'--------------------------------------------------------------------------
' Flash the lights on the Aardvark I2C/SPI Activity Board.
'--------------------------------------------------------------------------
' Redistribution and use of this file in source and binary forms, with
' or without modification, are permitted.
'
' THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
' "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
' LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
' FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
' COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
' INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
' BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
' LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
' CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
' LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
' ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
' POSSIBILITY OF SUCH DAMAGE.
'==========================================================================

'==========================================================================
' CONSTANTS
'==========================================================================
Const I2C_BITRATE = 100  'kHz


'==========================================================================
' FUNCTIONS
'==========================================================================
Sub flash_lights(handle)
    Dim data_out(1) As Byte
    data_out(0) = 0
    data_out(1) = 0

    Dim res As Long

    ' Configure I/O expander lines as outputs
    data_out(0) = &H3
    data_out(1) = &H0
    res = aa_i2c_write(handle, &H38, AA_I2C_NO_FLAGS, 2, data_out)
    If (res < 0) Then
        Exit Sub
    End If
    
    If (res = 0) Then
        Debug.Print ("error: slave device 0x38 not found")
        Exit Sub
    End If
    
    ' Turn lights on in sequence
    Dim i As Byte
    i = &HFF
    While (i <> 0)
        i = (i * 2) And &HFF
        data_out(0) = &H1
        data_out(1) = i
        res = aa_i2c_write(handle, &H38, AA_I2C_NO_FLAGS, 2, data_out)
        If (res < 0) Then
            Exit Sub
        End If
        aa_sleep_ms (70)
    Wend
        
    ' Leave lights on for 100 ms
    aa_sleep_ms (100)
    
    ' Turn lights off in sequence
    i = &H0
    While (i <> &HFF)
        i = (i * 2) Or &H1
        data_out(0) = &H1
        data_out(1) = i
        res = aa_i2c_write(handle, &H38, AA_I2C_NO_FLAGS, 2, data_out)
        If (res < 0) Then
            Exit Sub
        End If
        aa_sleep_ms (70)
    Wend

    aa_sleep_ms (100)
        
    ' Configure I/O expander lines as inputs
    data_out(0) = &H3
    data_out(1) = &HFF
    res = aa_i2c_write(handle, &H38, AA_I2C_NO_FLAGS, 2, data_out)
    If (res < 0) Then
        Exit Sub
    End If
End Sub


'==========================================================================
' MAIN PROGRAM
'==========================================================================
Sub aalights_run()
    Dim handle As Long

    ' Open the device
    handle = aa_open(0)
    If (handle <= 0) Then
        Debug.Print ("Unable to open Aardvark device on port 0")
        Debug.Print ("Error code = " & handle)
        Exit Sub
    End If
    
    ' Ensure that the I2C subsystem is enabled
    Call aa_configure(handle, AA_CONFIG_SPI_I2C)
    
    ' Enable the I2C bus pullup resistors (2.2k resistors).
    ' This command is only effective on v2.0 hardware or greater.
    ' The pullup resistors on the v1.02 hardware are enabled by default.
    Call aa_i2c_pullup(handle, AA_I2C_PULLUP_BOTH)

    ' Power the board using the Aardvark adapter's power supply.
    ' This command is only effective on v2.0 hardware or greater.
    ' The power pins on the v1.02 hardware are not enabled by default.
    Call aa_target_power(handle, AA_TARGET_POWER_BOTH)

    ' Set the bitrate
    Dim bitrate As Long
    bitrate = aa_i2c_bitrate(handle, I2C_BITRATE)
    Debug.Print ("Bitrate set to " & bitrate & " kHz")

    flash_lights (handle)
    
    ' Close the device and exit
    aa_close (handle)
End Sub
