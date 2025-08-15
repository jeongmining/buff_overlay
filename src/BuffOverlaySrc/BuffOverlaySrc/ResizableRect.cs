using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace BuffOverlay
{
    public class ResizableRect : FrameworkElement
    {
        public double HandleSize { get; set; } = 10;
        public Brush Stroke { get; set; } = Brushes.DeepSkyBlue;
        public double StrokeThickness { get; set; } = 2;
        public Brush Fill { get; set; } = new SolidColorBrush(Color.FromArgb(40, 0, 153, 255));

        public Rect Rect { get => _rect; set { _rect = value; InvalidateVisual(); } }
        Rect _rect;

        string? _active;    
        Point _startMouse;
        Rect _startRect;

        protected override void OnRender(DrawingContext dc)
        {
            base.OnRender(dc);
            dc.PushClip(new RectangleGeometry(new Rect(0, 0, ActualWidth, ActualHeight)));
            dc.DrawRectangle(Fill, new Pen(Stroke, StrokeThickness), Rect);
            foreach (var h in Handles())
                dc.DrawRectangle(Brushes.DeepSkyBlue, null, h);
            dc.Pop();
        }

        Rect[] Handles()
        {
            double s = HandleSize, x = Rect.X, y = Rect.Y, w = Rect.Width, h = Rect.Height;
            return new[]
            {
                new Rect(x-s/2, y-s/2, s, s),
                new Rect(x+w/2-s/2, y-s/2, s, s),
                new Rect(x+w-s/2, y-s/2, s, s),
                new Rect(x-s/2, y+h/2-s/2, s, s),
                new Rect(x+w-s/2, y+h/2-s/2, s, s),
                new Rect(x-s/2, y+h-s/2, s, s),
                new Rect(x+w/2-s/2, y+h-s/2, s, s),
                new Rect(x+w-s/2, y+h-s/2, s, s),
            };
        }

        string? Hit(Point p)
        {
            var hs = Handles();
            string[] names = { "tl", "tm", "tr", "ml", "mr", "bl", "bm", "br" };
            for (int i = 0; i < hs.Length; i++) if (hs[i].Contains(p)) return names[i];
            var inner = new Rect(Rect.X + HandleSize, Rect.Y + HandleSize, Rect.Width - 2 * HandleSize, Rect.Height - 2 * HandleSize);
            if (inner.Contains(p)) return "move";
            return null;
        }

        protected override void OnMouseDown(MouseButtonEventArgs e)
        {
            if (e.LeftButton == MouseButtonState.Pressed)
            {
                Focus();
                _startMouse = e.GetPosition(this);
                _startRect = Rect;
                _active = Hit(_startMouse);
                CaptureMouse();
                e.Handled = true;
            }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            var p = e.GetPosition(this);
            var h = Hit(p);
            Cursor = h switch
            {
                "tl" or "br" => Cursors.SizeNWSE,
                "tr" or "bl" => Cursors.SizeNESW,
                "ml" or "mr" => Cursors.SizeWE,
                "tm" or "bm" => Cursors.SizeNS,
                "move" => Cursors.SizeAll,
                _ => Cursors.Arrow
            };

            if (_active == null || e.LeftButton != MouseButtonState.Pressed) return;

            Vector d = p - _startMouse;
            var g = _startRect;

            if (_active == "move")
            {
                g.X += d.X; g.Y += d.Y;
            }
            else
            {
                double minw = 20, minh = 20;
                if (_active is "tl" or "ml" or "bl")
                {
                    double nl = g.Left + d.X;
                    if (g.Right - nl < minw) nl = g.Right - minw;
                    g.X = nl; g.Width = _startRect.Right - nl;
                }
                if (_active is "tr" or "mr" or "br")
                {
                    double nr = g.Right + d.X;
                    if (nr - g.Left < minw) nr = g.Left + minw;
                    g.Width = nr - g.Left;
                }
                if (_active is "tl" or "tm" or "tr")
                {
                    double nt = g.Top + d.Y;
                    if (g.Bottom - nt < minh) nt = g.Bottom - minh;
                    g.Y = nt; g.Height = _startRect.Bottom - nt;
                }
                if (_active is "bl" or "bm" or "br")
                {
                    double nb = g.Bottom + d.Y;
                    if (nb - g.Top < minh) nb = g.Top + minh;
                    g.Height = nb - g.Top;
                }
            }
            Rect = g;
            e.Handled = true;
        }

        protected override void OnMouseUp(MouseButtonEventArgs e)
        {
            if (_active != null)
            {
                _active = null;
                ReleaseMouseCapture();
                e.Handled = true;
            }
        }
    }
}
