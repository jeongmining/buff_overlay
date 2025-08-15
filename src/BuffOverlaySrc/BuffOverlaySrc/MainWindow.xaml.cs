using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

// 충돌 방지 별칭
using WF = System.Windows.Forms;
using SD = System.Drawing;
using SDI = System.Drawing.Imaging;

namespace BuffOverlay
{
    public partial class MainWindow : Window
    {
        const int GRIP_SIZE = 14;
        const int MIN_W = 180, MIN_H = 120;
        const string HINT_TEXT = "R: 영역 선택 • Wheel: 투명도 • 드래그: 이동 • 엣지/코너: 리사이즈";

        RectInt _captureRectPx;
        bool _hasRegion = false;
        double? _aspect = null;
        double _opacity = 0.9;

        DispatcherTimer _timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(33) };
        WriteableBitmap? _wb;
        HwndSource? _source;
        RECT _startSizingRect;

        public MainWindow()
        {
            InitializeComponent();
            this.Opacity = _opacity;
            _timer.Tick += (s, e) => UpdateFrame();
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            _source = (HwndSource)PresentationSource.FromVisual(this)!;
            _source.AddHook(WndProc);
            CenterOnPrimary();

            Hint.Content = HINT_TEXT;
            _hasRegion = false;
            UpdateHintVisibility();
            UpdateOutlineVisibility();
        }

        // ===== 프레임 업데이트 =====
        void UpdateFrame()
        {
            if (!_hasRegion || _captureRectPx.Width <= 0 || _captureRectPx.Height <= 0) return;

            using var bmp = new SD.Bitmap(_captureRectPx.Width, _captureRectPx.Height, SDI.PixelFormat.Format32bppPArgb);
            using (var g = SD.Graphics.FromImage(bmp))
            {
                g.CopyFromScreen(_captureRectPx.X, _captureRectPx.Y, 0, 0,
                    new SD.Size(_captureRectPx.Width, _captureRectPx.Height),
                    SD.CopyPixelOperation.SourceCopy);
            }

            var bmpData = bmp.LockBits(new SD.Rectangle(0, 0, bmp.Width, bmp.Height),
                                       SDI.ImageLockMode.ReadOnly,
                                       SDI.PixelFormat.Format32bppPArgb);

            if (_wb == null || _wb.PixelWidth != bmp.Width || _wb.PixelHeight != bmp.Height)
            {
                _wb = new WriteableBitmap(bmp.Width, bmp.Height, 96, 96, System.Windows.Media.PixelFormats.Pbgra32, null);
                PreviewImage.Source = _wb;
            }

            _wb.Lock();
            _wb.WritePixels(new Int32Rect(0, 0, bmp.Width, bmp.Height),
                            bmpData.Scan0, bmpData.Stride * bmpData.Height, bmpData.Stride);
            _wb.AddDirtyRect(new Int32Rect(0, 0, bmp.Width, bmp.Height));
            _wb.Unlock();

            bmp.UnlockBits(bmpData);
        }

        // ===== 영역 선택 =====
        void StartSelectOrFinish()
        {
            if (SelectionOverlay.ActiveInstance != null)
            {
                SelectionOverlay.ActiveInstance.Finish();
                return;
            }

            var overlay = new SelectionOverlay { Owner = this };
            overlay.Finished += rectPx =>
            {
                _captureRectPx = rectPx;
                _hasRegion = true;
                _aspect = (double)_captureRectPx.Width / _captureRectPx.Height;
                ResizeToAspect(anchorTL: true);
                if (!_timer.IsEnabled) _timer.Start();


                UpdateHintVisibility();
                UpdateOutlineVisibility();
            };
            overlay.Show();
            overlay.Activate();
        }

        // ===== 비율 고정 리사이즈 =====
        void ResizeToAspect(bool anchorTL)
        {
            if (_aspect == null) return;
            double newH = Math.Max(MIN_H, Math.Round(this.Width / _aspect.Value));
            double newW = Math.Max(MIN_W, Math.Round(newH * _aspect.Value));
            this.Width = newW;
            this.Height = newH;
        }

        RECT EnforceAspect(RECT g, uint edge, RECT start)
        {
            if (_aspect == null)
            {
                if ((g.Right - g.Left) < MIN_W) g.Right = g.Left + MIN_W;
                if ((g.Bottom - g.Top) < MIN_H) g.Bottom = g.Top + MIN_H;
                return g;
            }
            double A = _aspect.Value;
            int w = g.Right - g.Left;
            int h = g.Bottom - g.Top;
            int sw = start.Right - start.Left;
            int sh = start.Bottom - start.Top;

            bool horizOnly = (edge == Native.WMSZ_LEFT || edge == Native.WMSZ_RIGHT);
            bool vertOnly = (edge == Native.WMSZ_TOP || edge == Native.WMSZ_BOTTOM);

            if (horizOnly)
            {
                int newH = Math.Max(MIN_H, (int)Math.Round(w / A));
                if (edge == Native.WMSZ_TOP) g.Top = g.Bottom - newH; else g.Bottom = g.Top + newH;
            }
            else if (vertOnly)
            {
                int newW = Math.Max(MIN_W, (int)Math.Round(h * A));
                if (edge == Native.WMSZ_LEFT) g.Left = g.Right - newW; else g.Right = g.Left + newW;
            }
            else
            {
                int dw = w - sw, dh = h - sh;
                if (Math.Abs(dw) >= Math.Abs(dh))
                {
                    int newH = Math.Max(MIN_H, (int)Math.Round(w / A));
                    if (edge is Native.WMSZ_TOP or Native.WMSZ_TOPLEFT or Native.WMSZ_TOPRIGHT)
                        g.Top = g.Bottom - newH;
                    else g.Bottom = g.Top + newH;
                }
                else
                {
                    int newW = Math.Max(MIN_W, (int)Math.Round(h * A));
                    if (edge is Native.WMSZ_LEFT or Native.WMSZ_TOPLEFT or Native.WMSZ_BOTTOMLEFT)
                        g.Left = g.Right - newW;
                    else g.Right = g.Left + newW;
                }
            }
            if ((g.Right - g.Left) < MIN_W) g.Right = g.Left + MIN_W;
            if ((g.Bottom - g.Top) < MIN_H) g.Bottom = g.Top + MIN_H;
            return g;
        }

        // ===== 힌트/OSD =====
        void UpdateHintVisibility() =>
            Hint.Visibility = _hasRegion ? Visibility.Collapsed : Visibility.Visible;

        void SetOpacity(double value)
        {
            _opacity = Math.Clamp(value, 0.2, 1.0);
            this.Opacity = _opacity;
            ShowOsd($"Opacity: {(int)(_opacity * 100)}%");
        }

        void ShowOsd(string text, int ms = 800)
        {
            Osd.Content = text;
            Osd.Visibility = Visibility.Visible;
            var t = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(ms) };
            t.Tick += (s, e) => { Osd.Visibility = Visibility.Collapsed; t.Stop(); };
            t.Start();
        }

        // ===== 입력 =====
        private void Window_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.R) { StartSelectOrFinish(); e.Handled = true; return; }
            if (e.Key == Key.Escape) { Close(); return; }
            if (e.Key == Key.F12) { CenterOnPrimary(); return; }
            if (e.Key == Key.D0 && (Keyboard.Modifiers & ModifierKeys.Control) != 0) { SetOpacity(1.0); return; }

            int step = (Keyboard.Modifiers & ModifierKeys.Shift) != 0 ? 80 : 20;
            var g = new Rect(this.Left, this.Top, this.Width, this.Height);
            bool handled = false;

            if (e.Key == Key.Left)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Control) != 0) { g.Width = Math.Max(MIN_W, g.Width - step); handled = true; }
                else { g.X -= step; handled = true; }
            }
            else if (e.Key == Key.Right)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Control) != 0) { g.Width += step; handled = true; }
                else { g.X += step; handled = true; }
            }
            else if (e.Key == Key.Up)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Control) != 0) { g.Height = Math.Max(MIN_H, g.Height - step); handled = true; }
                else { g.Y -= step; handled = true; }
            }
            else if (e.Key == Key.Down)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Control) != 0) { g.Height += step; handled = true; }
                else { g.Y += step; handled = true; }
            }

            if (handled)
            {
                if ((Keyboard.Modifiers & ModifierKeys.Control) != 0 && _aspect != null)
                {
                    var r = new RECT((int)g.X, (int)g.Y, (int)(g.X + g.Width), (int)(g.Y + g.Height));
                    r = EnforceAspect(r, Native.WMSZ_BOTTOMRIGHT,
                        new RECT((int)this.Left, (int)this.Top, (int)(this.Left + this.Width), (int)(this.Top + this.Height)));
                    this.Left = r.Left; this.Top = r.Top; this.Width = r.Right - r.Left; this.Height = r.Bottom - r.Top;
                }
                else
                {
                    this.Left = g.X; this.Top = g.Y; this.Width = g.Width; this.Height = g.Height;
                }
                e.Handled = true;
            }
        }

        private void Window_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            SetOpacity(_opacity + (e.Delta > 0 ? 0.05 : -0.05));
        }

        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            var p = e.GetPosition(this);
            if (!IsOnEdge(p)) this.DragMove();
        }

        private void Window_MouseMove(object sender, MouseEventArgs e)
        {
        }

        bool IsOnEdge(Point p)
        {
            return p.X <= GRIP_SIZE || p.X >= (this.ActualWidth - GRIP_SIZE) ||
                   p.Y <= GRIP_SIZE || p.Y >= (this.ActualHeight - GRIP_SIZE);
        }

        void CenterOnPrimary()
        {
            var wa = SystemParameters.WorkArea;
            this.Left = wa.Left + (wa.Width - this.Width) / 2;
            this.Top = wa.Top + (wa.Height - this.Height) / 2;
        }

        // ===== Win32 훅: 엣지 리사이즈/비율고정 =====
        IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            switch ((uint)msg)
            {
                case Native.WM_NCHITTEST:
                    {
                        var mp = WF.Control.MousePosition;
                        var pt = this.PointFromScreen(new Point(mp.X, mp.Y));
                        int w = (int)this.ActualWidth, h = (int)this.ActualHeight;

                        bool left = pt.X <= GRIP_SIZE;
                        bool right = pt.X >= w - GRIP_SIZE;
                        bool top = pt.Y <= GRIP_SIZE;
                        bool bottom = pt.Y >= h - GRIP_SIZE;

                        if (left && top) { handled = true; return (IntPtr)Native.HTTOPLEFT; }
                        if (right && top) { handled = true; return (IntPtr)Native.HTTOPRIGHT; }
                        if (left && bottom) { handled = true; return (IntPtr)Native.HTBOTTOMLEFT; }
                        if (right && bottom) { handled = true; return (IntPtr)Native.HTBOTTOMRIGHT; }
                        if (left) { handled = true; return (IntPtr)Native.HTLEFT; }
                        if (right) { handled = true; return (IntPtr)Native.HTRIGHT; }
                        if (top) { handled = true; return (IntPtr)Native.HTTOP; }
                        if (bottom) { handled = true; return (IntPtr)Native.HTBOTTOM; }

                        handled = false;
                        return IntPtr.Zero;
                    }
                case Native.WM_ENTERSIZEMOVE:
                    _startSizingRect = GetWindowRect();
                    break;
                case Native.WM_SIZING:
                    {
                        if (_aspect != null)
                        {
                            var edge = (uint)wParam;
                            var r = Marshal.PtrToStructure<RECT>(lParam);
                            r = EnforceAspect(r, edge, _startSizingRect);
                            Marshal.StructureToPtr(r, lParam, true);
                            handled = true;
                        }
                        break;
                    }
            }
            return IntPtr.Zero;
        }

        RECT GetWindowRect()
        {
            Native.GetWindowRect(new WindowInteropHelper(this).Handle, out RECT r);
            return r;
        }

        void UpdateOutlineVisibility()
        {
            Outline.Visibility = _hasRegion ? Visibility.Collapsed : Visibility.Visible;
        }

    }

    public readonly struct RectInt
    {
        public readonly int X, Y, Width, Height;
        public RectInt(int x, int y, int w, int h) { X = x; Y = y; Width = w; Height = h; }
    }
}
