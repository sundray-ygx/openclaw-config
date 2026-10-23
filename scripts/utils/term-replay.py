#!/usr/bin/env python3
"""回放真实 TUI 字节流到当前终端——复现器/二分工具。

用法:
  python3 term-replay.py <capture.bin> [--from N] [--to N] [--pace]
  --pace   按原始节奏回放(默认全速)
捕获文件由 tmux pipe-pane 录制（含 TUI 全部原始输出字节）。
"""
import os, sys, time

def main():
    if not sys.stdout.isatty():
        print("请在真实终端中运行"); sys.exit(1)
    path = sys.argv[1]
    args = sys.argv[2:]
    frm = int(args[args.index('--from')+1]) if '--from' in args else 0
    to = int(args[args.index('--to')+1]) if '--to' in args else None
    pace = '--pace' in args
    data = open(path, 'rb').read()
    if to is not None:
        data = data[frm:to]
    elif frm:
        data = data[frm:]
    fd = os.open('/dev/tty', os.O_WRONLY)
    os.write(fd, b"\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")  # 备用屏+清屏
    try:
        if pace:
            # 简单分块回放（~4KB/块, 10ms 间隔近似原节奏）
            for i in range(0, len(data), 4096):
                os.write(fd, data[i:i+4096])
                time.sleep(0.01)
        else:
            os.write(fd, data)
        time.sleep(0.5)
        banner = "\x1b[H\x1b[7m  回放完成(共%d字节) 截图后按回车退出  \x1b[27m" % len(data)
        os.write(fd, banner.encode())
        import termios, tty
        old = termios.tcgetattr(0)
        tty.setraw(0)
        try:
            sys.stdin.buffer.read(1)
        finally:
            termios.tcsetattr(0, termios.TCSADRAIN, old)
    finally:
        os.write(fd, b"\x1b[?25h\x1b[?1049l")
        os.close(fd)

if __name__ == '__main__':
    main()
