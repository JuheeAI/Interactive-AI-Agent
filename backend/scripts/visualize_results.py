import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import math

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
RESULT_DIR = os.path.join(BASE_DIR, "data", "benchmark_results")
OUTPUT_PATH = os.path.join(RESULT_DIR, "final_summary_board_fixed.jpg")

def generate_summary_board():
    report_path = os.path.join(RESULT_DIR, "final_report.csv")
    if not os.path.exists(report_path):
        print("리포트를 찾을 수 없습니다.")
        return
    
    df = pd.read_csv(report_path)
    df['CLIP'] = pd.to_numeric(df['CLIP'], errors='coerce')
    img_gen_df = df.dropna(subset=['CLIP'])
    
    img_files = sorted([f for f in os.listdir(RESULT_DIR) if f.endswith('.jpg') and f.split('_')[0].isdigit()], 
                       key=lambda x: int(x.split('_')[0]))

    cols = 10
    rows = math.ceil(len(img_files) / cols)
    thumb_size = 400 
    
    canvas_w = cols * thumb_size
    canvas_h = (rows * thumb_size) + 800 # 하단 여백 최적화
    
    summary_board = Image.new("RGB", (canvas_w, canvas_h), (15, 15, 20))
    draw = ImageDraw.Draw(summary_board)
    
    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(font_path):
        alt_paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        for p in alt_paths:
            if os.path.exists(p): font_path = p; break

    try:
        # --- [수정] 폰트 크기 밸런스 조정 ---
        font_header = ImageFont.truetype(font_path, 90) # 헤더 (기존 100 대용)
        font_main = ImageFont.truetype(font_path, 65)   # 본문 (기존 80 대용)
        font_label = ImageFont.truetype(font_path, 45)  # ID 라벨
    except:
        font_header = font_main = font_label = ImageFont.load_default()

    for idx, filename in enumerate(img_files):
        img_path = os.path.join(RESULT_DIR, filename)
        try:
            with Image.open(img_path) as img:
                img = img.resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                x = (idx % cols) * thumb_size
                y = (idx // cols) * thumb_size
                
                case_id = int(filename.split('_')[0])
                status = df.loc[df['ID'] == case_id, 'Self-Check'].values[0]
                accent_color = (0, 255, 100) if status == "PASS" else (255, 50, 50)
                
                summary_board.paste(img, (x, y))
                draw.rectangle([x, y, x + thumb_size, y + thumb_size], outline=accent_color, width=12)
                draw.rectangle([x, y, x + 180, y + 80], fill=accent_color)
                draw.text((x + 20, y + 10), f"ID {case_id}", fill=(0, 0, 0), font=font_label)
        except: continue

    # --- [수정] 하단 통계 섹션 간격 최적화 ---
    avg_clip = img_gen_df['CLIP'].mean()
    pass_rate = (img_gen_df['Self-Check'] == 'PASS').sum() / len(img_gen_df) * 100
    
    rect_y_start = rows * thumb_size + 80
    draw.rectangle([100, rect_y_start, canvas_w - 100, canvas_h - 100], outline=(100, 100, 100), width=5)
    
    # 간격 변수 설정
    current_y = rect_y_start + 60

    # 1. 헤더
    draw.text((200, current_y), "AGENT SYSTEM STRESS TEST SUMMARY", fill=(255, 255, 255), font=font_header)
    
    # 2. 구분선 (헤더 바로 아래로 바싹 붙임)
    current_y += 100 
    draw.text((200, current_y), "-" * 70, fill=(100, 100, 100), font=font_main)
    
    # 3. 본문 (구분선과 밀착)
    current_y += 60 
    stats_body = (
        f"Total Images Tested : {len(img_gen_df)} units\n"
        f"Average CLIP Score  : {avg_clip:.2f}\n"
        f"Self-Check PASS Rate: {pass_rate:.1f} %\n"
        f"Avg System Latency  : {df['Time(s)'].mean():.2f} sec\n"
        f"Peak GPU Memory     : {df['Mem(MB)'].max():.0f} MB"
    )
    
    draw.text((200, current_y), stats_body, fill=(230, 230, 230), font=font_main, spacing=20)

    summary_board.save(OUTPUT_PATH, "JPEG", quality=95)
    print(f"✅ 리포트 시각화 최적화 완료: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_summary_board()