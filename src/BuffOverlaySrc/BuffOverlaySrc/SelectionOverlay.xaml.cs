using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace BuffOverlay
{
    public partial class SelectionOverlay : Window
    {
        public static SelectionOverlay? ActiveInstance { get; private set; } 
        public event Action<RectInt>? Finished;                         

        public SelectionOverlay()
        {
            InitializeComponent();
            ActiveInstance = this;

            Left = SystemParameters.VirtualScreenLeft;
            Top = SystemParameters.VirtualScreenTop;
            Width = SystemParameters.VirtualScreenWidth;
            Height = SystemParameters.VirtualScreenHeight;

            double w = 480, h = 320;
            var cx = Left + Width / 2; var cy = Top + Height / 2;
            Selector.Rect = new Rect(cx - w / 2, cy - h / 2, w, h);

            CompositionTarget.Rendering += (_, __) => RedrawMask();
        }

        void RedrawMask()
        {
            var full = new RectangleGeometry(new Rect(0, 0, ActualWidth, ActualHeight));
            var hole = new RectangleGeometry(Selector.Rect);
            var grp = new GeometryGroup { FillRule = FillRule.EvenOdd };
            grp.Children.Add(full); grp.Children.Add(hole);
            Dimmer.Data = grp;
        }

        void Window_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.R) { Finish(); e.Handled = true; }
            if (e.Key == Key.Escape) { Close(); }
        }

        public void Finish()
        {
            var dpi = VisualTreeHelper.GetDpi(this);
            int x = (int)Math.Round(Selector.Rect.X * dpi.DpiScaleX + SystemParameters.VirtualScreenLeft);
            int y = (int)Math.Round(Selector.Rect.Y * dpi.DpiScaleY + SystemParameters.VirtualScreenTop);
            int w = (int)Math.Round(Selector.Rect.Width * dpi.DpiScaleX);
            int h = (int)Math.Round(Selector.Rect.Height * dpi.DpiScaleY);
            Finished?.Invoke(new RectInt(x, y, w, h));
            Close();
        }

        void Window_MouseDown(object sender, MouseButtonEventArgs e) => this.Focus();

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            ActiveInstance = null;
        }
    }
}
