# -*- coding: utf-8 -*-
"""
IUH EVENT SNIPER PRO - Discord Bot Chuyên Nghiệp
Cấu hình đã điền sẵn 100% Token, Channel ID và Cookie của bạn
"""

import time
import requests
from bs4 import BeautifulSoup
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View

# ==============================================================================
# CẤU HÌNH BOT & TÀI KHOẢN (ĐÃ ĐIỀN CHUẨN 100%)
# ==============================================================================
DISCORD_BOT_TOKEN       = "MTU1ODM3MTgxMjMxMDY1NTEwNg.GHSHCc.nN1Dg_nvAIgQnXZcuwRzTljCGckFE7sjlMEuu0"
NOTIFICATION_CHANNEL_ID = 1558370434339180636

COOKIE_PHPSESSID        = "hqflc37ikcopc3j2nfb2iskfk6"
MAIN_PAGE_URL           = "https://doantn.iuh.edu.vn/doanvien.html"
SCAN_SECONDS            = 60  # Quét liên tục mỗi 60 giây
# ==============================================================================

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class OpenWebButton(View):
    """Nút bấm dẫn thẳng vào trang đăng ký IUH"""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="🚀 MỞ TRANG ĐĂNG KÝ NGAY", url=MAIN_PAGE_URL, style=discord.ButtonStyle.link))


def fetch_iuh_activities():
    """Hàm cào dữ liệu từ web trường IUH"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": f"PHPSESSID={COOKIE_PHPSESSID}",
    }
    try:
        res = requests.get(MAIN_PAGE_URL, headers=headers, timeout=15)
        if "Dương Thế Phát" not in res.text and "tblDoanvien" not in res.text:
            return None, False

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="tblDoanvien")
        if not table:
            return [], False

        rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
        activities = []
        has_slot = False

        for idx, row in enumerate(rows):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            name = cells[1].get_text(strip=True)
            diem = cells[3].get_text(strip=True)
            han = cells[4].get_text(strip=True)
            status = cells[5].get_text(strip=True)

            is_full = any(kw in status for kw in ["Đã đủ số lượng", "Hết chỗ", "Đã kết thúc"])
            has_btn = bool(cells[5].find(["input", "button", "a"])) or "Đăng ký" in status
            can_reg = (not is_full) and has_btn

            if can_reg:
                has_slot = True

            activities.append({
                "stt": idx + 1,
                "name": name,
                "diem": diem,
                "han": han,
                "status": status,
                "can_reg": can_reg
            })

        return activities, has_slot
    except Exception as e:
        print(f"❌ Lỗi kết nối IUH: {e}")
        return [], False


# ==============================================================================
# VÒNG LẶP QUÉT & THÔNG BÁO MỖI 60 GIÂY
# ==============================================================================
@tasks.loop(seconds=SCAN_SECONDS)
async def monitor_task():
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
    if not channel:
        print(f"⚠️ Chưa tìm thấy kênh có ID: {NOTIFICATION_CHANNEL_ID}")
        return

    activities, has_slot = fetch_iuh_activities()
    if activities is None:
        await channel.send("⚠️ **CẢNH BÁO:** Cookie IUH đã hết hạn! Hãy đăng nhập lại trên web để lấy Cookie mới.")
        return

    now_str = time.strftime("%H:%M:%S")

    # 1. NẾU CÓ SLOT MỞ -> HỘP MÀU ĐỎ RỰC + TAG @everyone BÁO ĐỘNG KHẨN CẤP
    if has_slot:
        urgent_embed = discord.Embed(
            title="🚨 CÓ HOẠT ĐỘNG MỞ ĐĂNG KÝ! VÀO GIẬT SLOT NGAY!",
            color=0xe74c3c,  # Màu đỏ khẩn cấp
            timestamp=discord.utils.utcnow()
        )
        urgent_embed.set_author(name="Dương Thế Phát • IUH Event Sniper Pro", icon_url="https://doantn.iuh.edu.vn/templates/images/logo.png")

        for act in activities:
            if act["can_reg"]:
                urgent_embed.add_field(
                    name=f"🔥 {act['name']}",
                    value=f"⭐ **Điểm rèn luyện:** `+{act['diem']} điểm`\n📅 **Hạn đăng ký:** `{act['han']}`\n⚡ **Trạng thái:** `{act['status']}`",
                    inline=False
                )

        urgent_embed.set_footer(text=f"Phát hiện lúc {now_str} • Bấm nút bên dưới để mở web")
        view = OpenWebButton()
        await channel.send(content="@everyone ⚡ **CÓ HOẠT ĐỘNG MỞ CHỖ! VÀO ĐĂNG KÝ NGAY!**", embed=urgent_embed, view=view)

    # 2. BÌNH THƯỜNG -> HỘP XANH LÁ MỖI 60S (KHÔNG TAG ĐỂ TRÁNH SPAM CHUÔNG)
    else:
        normal_embed = discord.Embed(
            title=f"⏱ BÁO CÁO ĐỊNH KỲ (60 GIÂY) — {now_str}",
            color=0x2ecc71,  # Màu xanh lá
            timestamp=discord.utils.utcnow()
        )
        normal_embed.set_author(name="Dương Thế Phát • 26654621", icon_url="https://doantn.iuh.edu.vn/templates/images/logo.png")

        if not activities:
            normal_embed.description = "*(Chưa có hoạt động nào trong danh sách)*"
        else:
            list_text = ""
            for act in activities:
                list_text += f"• **{act['name']}**\n  👉 Điểm: `{act['diem']}` | Hạn: `{act['han']}` | TT: *{act['status']}*\n\n"
            normal_embed.description = list_text

        normal_embed.set_footer(text="Chu kỳ: 60s/lần • Khi có slot mở sẽ tự động đổi sang màu đỏ & tag @everyone")
        await channel.send(embed=normal_embed)


@bot.event
async def on_ready():
    print(f"✨ [Discord Bot] Đã Online thành công với tên: {bot.user}")
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
    if channel:
        start_embed = discord.Embed(
            title="🟢 IUH EVENT SNIPER PRO ĐÃ BẬT!",
            description="👤 **Sinh viên:** Dương Thế Phát\n⏱ **Chu kỳ:** Quét liên tục 60 giây/lần\n⚡ **Trạng thái:** Bot đang canh 24/7 và sẽ tự động ping `@everyone` khi có slot mở!",
            color=0x3498db,
            timestamp=discord.utils.utcnow()
        )
        await channel.send(embed=start_embed, view=OpenWebButton())

    if not monitor_task.is_running():
        monitor_task.start()


if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
