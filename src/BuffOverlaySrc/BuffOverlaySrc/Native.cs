using System;
using System.Runtime.InteropServices;

namespace BuffOverlay
{
    public static class Native
    {
        public const uint WM_NCHITTEST = 0x0084;
        public const int HTLEFT = 10, HTRIGHT = 11, HTTOP = 12, HTTOPLEFT = 13, HTTOPRIGHT = 14, HTBOTTOM = 15, HTBOTTOMLEFT = 16, HTBOTTOMRIGHT = 17, HTCAPTION = 2;

        public const uint WM_SIZING = 0x0214;
        public const uint WM_ENTERSIZEMOVE = 0x0231;
        public const uint WM_EXITSIZEMOVE = 0x0232;
        public const uint WMSZ_LEFT = 1, WMSZ_RIGHT = 2, WMSZ_TOP = 3, WMSZ_TOPLEFT = 4, WMSZ_TOPRIGHT = 5, WMSZ_BOTTOM = 6, WMSZ_BOTTOMLEFT = 7, WMSZ_BOTTOMRIGHT = 8;

        [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; public RECT(int l, int t, int r, int b) { Left = l; Top = t; Right = r; Bottom = b; } }
}
