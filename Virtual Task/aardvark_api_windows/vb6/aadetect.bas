Attribute VB_Name = "aadetect"
'==========================================================================
' (c) 2004  Total Phase, Inc.
'--------------------------------------------------------------------------
' Project : Aardvark Sample Code
' File    : aadetect.bas
'--------------------------------------------------------------------------
' Auto-detection test routine
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
' MAIN PROGRAM
'==========================================================================
Public Sub aadetect_run()
    Debug.Print ("Detecting Aardvark adapters...")
    Dim num As Long
    Dim devices(15) As Integer

    ' Find all the attached devices
    num = aa_find_devices(16, devices)

    If num > 0 Then
        Debug.Print ("Found " & num & " device(s)")

        Dim port As Integer
        Dim inuse As String
        Dim i As Long

        ' Print the information on each device
        For i = 0 To num - 1
            port = devices(i)

            ' Determine if the device is in-use
            inuse = "   (avail)"
            If port And AA_PORT_NOT_FREE Then
                inuse = "   (in-use)"
                port = port And Not AA_PORT_NOT_FREE
            End If

            ' Display device port number, in-use status, and serial number
            Debug.Print ("    port = " & port & inuse)
        Next
    Else
        Debug.Print ("No devices found.")
    End If
End Sub
