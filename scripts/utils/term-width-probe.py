#!/usr/bin/env python3
"""终端宽度行为探针：实测当前终端对歧义宽度字符的真实渲染宽度。

原理：把光标定位到行首已知列，打印 N 个测试字符，然后发 DSR(CSI 6n)
读回光标真实列位置，差值 / N = 每字符实际占用格数。

用法：在【你平时跑 hermes TUI 的那个终端】里直接运行：
    python3 /root/scripts/utils/term-width-probe.py
"""
import sys, tty, termios, select

def read_dsr(fd, timeout=1.0):
    """读取 CSI 6n 的应答 \x1b[row;colR，返回 (row, col)。"""
    import os
    os.write(fd, b"\x1b[6n")
    buf = b""
    while True:
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None
        import os as _os
        ch = _os.read(fd, 1)
        if ch == b"":
            return None
        buf += ch
        if ch == b"R":
            break
    s = buf.decode("ascii", "replace")
    if not (s.startswith("\x1b[") and s.endswith("R")):
        return None
    try:
        row, col = s[2:-1].split(";")
        return int(row), int(col)
    except ValueError:
        return None

def measure(fd, label, char, n=10):
    """在独立一行打印 n 个 char，返回每字符格宽（浮点）或 None。"""
    import os
    # 新起一行（终端可能处于任何状态），\r\n 前先清行
    os.write(fd, ("\r\n" + " " * 40 + "\r").encode())
    pos0 = read_dsr(fd)
    if not pos0:
        print(f"[{label}] 终端不响应光标位置查询(CSI 6n)，无法测量")
        return None
    os.write(fd, (char * n).encode())
    pos1 = read_dsr(fd)
    if not pos1:
        print(f"[{label}] 第二次查询失败")
        return None
    if pos1[0] != pos0[0]:
        print(f"[{label}] 光标换行了(起始列{pos0[1]}→行{pos1[0]}列{pos1[1]})，行宽不够，请把终端窗口加宽后重试")
        return None
    per = (pos1[1] - pos0[1]) / n
    return per

def wrap_test(fd):
    """精确满行行为：从行首打印 cols 个字符后，合规终端(deferred wrap)光标
    应停在同行第 cols 列；eager wrap 客户端会立即跳到下一行第 1 列——
    这会让 TUI 的行模型整体错位一格。"""
    import os, shutil
    cols = shutil.get_terminal_size(fallback=(120, 30)).columns
    # 先下移再上移，确保测试行不在屏幕底部（避免触发滚动干扰）
    os.write(fd, ("\r\n\r\n\r\n" + "\x1b[2A" + "\x1b[K").encode())
    pos0 = read_dsr(fd)
    if not pos0:
        return None
    os.write(fd, (("\r" + "A" * cols)).encode())
    pos1 = read_dsr(fd)
    if not pos1:
        return None
    return cols, pos0, pos1

def pos_tests(fd):
    """三位数转义参数测试：200列宽终端下 CUP/CUF/CHA 参数>99 是否被正确解析。
    部分客户端截断三位数参数 → TUI 光标定位错列 → 周期性平铺乱码。"""
    import os, shutil
    cols = shutil.get_terminal_size(fallback=(120, 30)).columns
    rows = shutil.get_terminal_size(fallback=(120, 30)).lines
    results = []
    def cup_check(name, seq, expect_col, expect_row=None):
        # 合规终端会把超界定位钳制到最后一行/列
        ecol = min(expect_col, cols)
        erow = min(expect_row, rows) if expect_row else None
        os.write(fd, seq)
        p = read_dsr(fd)
        if not p:
            results.append((name, None, (erow, ecol)))
            return
        results.append((name, (p[0], p[1]), (erow if erow else p[0], ecol)))

    # CUP 三位数列: 定位到 10行 150列
    cup_check("CUP定位150列 (CSI 10;150H)", b"\x1b[10;150H", 150, 10)
    # CUP 三位数行+列: 25行 180列
    cup_check("CUP定位25行180列 (CSI 25;180H)", b"\x1b[25;180H", 180, 25)
    # CHA 水平绝对定位 175列 (CSI 175G)
    cup_check("CHA定位175列 (CSI 175G)", b"\x1b[175G", 175)
    # CUF 前移105格: 10行1列 + CSI 105C → 106列
    cup_check("CUF前移105格 (CSI 105C)", b"\x1b[10;1H\x1b[105C", 106, 10)
    # CUB 后移108格: 10行110列 + CSI 108D → 2列
    cup_check("CUB后移108格 (CSI 108D)", b"\x1b[10;110H\x1b[108D", 2, 10)
    # CUD 下移33行: 10行 → 43行
    cup_check("CUD下移33行 (CSI 33B)", b"\x1b[10;1H\x1b[33B", 1, 43)
    return results

def pending_wrap_cr_test(fd):
    """pending-wrap 状态下的 CR 行为：写满整行使光标进入 pending wrap，
    然后发 CR。规范(xterm)：CR 停在【同一行】第1列。
    若终端报了下一行 → TUI 每帧的所有写入都会整体错一行 = 乱码根因。"""
    import os, shutil
    cols = shutil.get_terminal_size(fallback=(120, 30)).columns
    os.write(fd, ("\r\n\r\n\r\n" + "\x1b[2A").encode())
    pos0 = read_dsr(fd)
    if not pos0:
        return None
    os.write(fd, ("\r" + "B" * cols).encode())   # 写满整行 → pending wrap
    pos1 = read_dsr(fd)
    os.write(fd, b"\r")                           # CR：应回本行行首
    pos2 = read_dsr(fd)
    return pos0, pos1, pos2

def wide_char_edge_tests(fd):
    """宽字符行尾边界行为（Ink SpacerHead 依赖）：
    a) 行尾剩1格时写宽字符 → 规范：换到下一行绘制(占1-2格), 光标第3格
    b) 行尾剩2格恰好放下 → 规范：占末两格, 光标 pending-wrap 停本行
    c) 复合帧模式：CJK串+SGR+ASCII串 → 光标应=模型计算值"""
    import os, shutil
    cols = shutil.get_terminal_size(fallback=(120, 30)).columns
    rows = shutil.get_terminal_size(fallback=(120, 30)).lines
    out = []
    # 上一块空行
    os.write(fd, ("\r\n\r\n\r\n\x1b[2A").encode())
    p0 = read_dsr(fd)
    if not p0:
        return None
    r0 = p0[0]
    if r0 + 2 > rows:  # 保证下面两行可用
        r0 = max(5, rows - 3)
        os.write(fd, f"\x1b[{r0};1H".encode())
    # a) 最后1格写宽字符
    os.write(fd, f"\x1b[{r0};{cols}H".encode())
    os.write(fd, "中".encode())
    pa = read_dsr(fd)
    # b) 剩2格恰好放下
    os.write(fd, f"\x1b[{r0};{cols-1}H".encode())
    os.write(fd, "中".encode())
    pb = read_dsr(fd)
    # c) 复合：CJK+SGR+ASCII
    os.write(fd, f"\x1b[{r0};1H".encode())
    os.write(fd, "中文abc\x1b[0mXY".encode())
    pc = read_dsr(fd)
    return (r0, cols, pa, pb, pc)

def main():
    if not sys.stdout.isatty():
        print("请在真实终端(非管道)中运行"); sys.exit(1)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    old_lflags = old[3]
    tty.setraw(fd)
    # 隐藏光标，减少闪烁
    import os
    os.write(fd, b"\x1b[?25l")
    try:
        tests = [
            ("ASCII 基准 A", "A", 1.0),
            ("CJK 中文(应恒为2)", "中", 2.0),
            ("制表符 ─ (U+2500 歧义)", "─", 1.0),
            ("轻阴影 ░ (U+2591 歧义, 进度条用)", "░", 1.0),
            ("勾号 ✓ (U+2713 歧义)", "✓", 1.0),
            ("间隔号 · (U+00B7 歧义)", "·", 1.0),
            ("箭头 ↑ (U+2191 歧义)", "↑", 1.0),
        ]
        results = []
        for label, ch, expect in tests:
            per = measure(fd, label, ch)
            if per is None:
                results.append((label, None, expect))
            else:
                mark = "OK" if abs(per - expect) < 0.01 else "!!! 偏离"
                print(f"\r\n[{label}] 实测每字符 {per:.1f} 格 (Hermes按 {expect:.0f} 格计算) {mark}\x1b[K")
                results.append((label, per, expect))
        print("\r\n" + "=" * 60 + "\x1b[K")
        w = wrap_test(fd)
        if w:
            cols, p0, p1 = w
            if p1[0] == p0[0]:
                print(f"\r\n[精确满行] 光标仍在第{p1[0]}行 第{p1[1]}列 (deferred wrap, 合规)\x1b[K")
            else:
                print(f"\r\n[精确满行] !!! 光标跳到 第{p1[0]}行 第{p1[1]}列 (eager wrap, 不合规——TUI 行模型会错位)\x1b[K")
        else:
            print("\r\n[精确满行] 测量失败\x1b[K")
        print("\r\n--- 三位数转义参数测试 ---\x1b[K")
        for name, got, want in pos_tests(fd):
            if got is None:
                print(f"\r\n[{name}] 无响应\x1b[K")
            elif got == want:
                print(f"\r\n[{name}] 实际({got[0]};{got[1]}) 期望({want[0]};{want[1]}) OK\x1b[K")
            else:
                print(f"\r\n[{name}] !!! 实际({got[0]};{got[1]}) 期望({want[0]};{want[1]}) 偏离\x1b[K")
        pw = pending_wrap_cr_test(fd)
        if pw:
            p0, p1, p2 = pw
            if p2[0] == p0[0]:
                print(f"\r\n[pending-wrap后CR] 写满行后光标在第{p1[0]}行第{p1[1]}列, CR后回到第{p2[0]}行第{p2[1]}列 (同行, 合规)\x1b[K")
            else:
                print(f"\r\n[pending-wrap后CR] !!! 写满行后光标在第{p1[0]}行第{p1[1]}列, CR后跳到第{p2[0]}行第{p2[1]}列 (换行, 不合规——TUI 每帧整体错一行, 高度疑似乱码根因)\x1b[K")
        else:
            print("\r\n[pending-wrap后CR] 测量失败\x1b[K")
        wc = wide_char_edge_tests(fd)
        if wc:
            r0, cols, pa, pb, pc = wc
            # a) 期望: 换行后占1-2格, 光标在 r0+1 行第3列
            if pa and pa[0] == r0 + 1 and pa[1] == 3:
                print(f"\r\n[行尾1格写宽字符] 换行绘制,光标({pa[0]};{pa[1]}) 期望({r0+1};3) OK\x1b[K")
            elif pa:
                print(f"\r\n[行尾1格写宽字符] !!! 实际({pa[0]};{pa[1]}) 期望({r0+1};3) 偏离——终端未按规范换行,行模型从此错位\x1b[K")
            else:
                print("\r\n[行尾1格写宽字符] 无响应\x1b[K")
            # b) 期望: 占末两格, pending-wrap 停本行第cols+1列
            if pb and pb[0] == r0 and pb[1] >= cols:
                print(f"\r\n[行尾2格写宽字符] 恰好放下,光标({pb[0]};{pb[1]}) 期望({r0};{cols}或{cols+1}) OK\x1b[K")
            elif pb:
                print(f"\r\n[行尾2格写宽字符] !!! 实际({pb[0]};{pb[1]}) 期望({r0};{cols}或{cols+1}) 偏离\x1b[K")
            else:
                print("\r\n[行尾2格写宽字符] 无响应\x1b[K")
            # c) 期望: 中文abcXY = 2+2+3+2=9格, 光标第10列
            if pc and pc[0] == r0 and pc[1] == 10:
                print(f"\r\n[复合帧CJK+SGR+ASCII] 光标({pc[0]};{pc[1]}) 期望({r0};10) OK\x1b[K")
            elif pc:
                print(f"\r\n[复合帧CJK+SGR+ASCII] !!! 实际({pc[0]};{pc[1]}) 期望({r0};10) 偏离\x1b[K")
            else:
                print("\r\n[复合帧CJK+SGR+ASCII] 无响应\x1b[K")
        print("\r\n" + "=" * 60 + "\x1b[K")
        bad = [r for r in results if r[1] is not None and abs(r[1] - r[2]) >= 0.5]
        cjk_ok = any(r[0].startswith("CJK") and r[1] == 2.0 for r in results)
        if bad:
            print("\r\n结论：你的终端把下列字符渲染成了与 Hermes 计算不同的宽度：\x1b[K")
            for label, per, exp in bad:
                print(f"\r\n  - {label}: 实测{per:.1f}格, Hermes计算{exp:.0f}格\x1b[K")
            print("\r\n这证实乱码根因：宽度模型不一致 → 局部重绘擦不干净 → 残留/重复。\x1b[K")
            print("\r\n修复方向：在 SSH 客户端关闭『歧义宽度字符按宽字符渲染』选项，\x1b[K")
            print("\r\n          或换用 Windows Terminal 等合规终端。\x1b[K")
        elif cjk_ok:
            print("\r\n结论：宽度行为全部与 Hermes 一致，宽度歧义不是根因，\x1b[K")
            print("\r\n      请把本输出发给小群继续排查（可能需检查 DECSTBM/同步输出行为）。\x1b[K")
    finally:
        os.write(fd, b"\x1b[?25h\r\n")
        tc = termios.tcgetattr(fd)
        tc[3] = old_lflags
        termios.tcsetattr(fd, termios.TCSADRAIN, tc)

if __name__ == "__main__":
    main()
