import os
import re

def check_and_rename_videos(folder):
    # 規則：01-15_(gallery/travel/boss/museum/bowling/candy)_(C/L).mp4
    VALID_PATTERN = re.compile(r'^(0[1-9]|1[0-5])_(gallery|travel|boss|museum|bowling|candy)_(C|L)\.mp4$')

    def suggest_filename(filename):
        parts = re.findall(r'(\d{2}|gallery|travel|boss|museum|bowling|candy|C|L)', filename)
        nums = [p for p in parts if re.match(r'\d{2}', p)]
        types = [p for p in parts if p in ['gallery','travel','boss','museum','bowling','candy']]
        sides = [p for p in parts if p in ['C','L']]
        num = nums[0] if nums else '01'
        typ = types[0] if types else 'unknown'
        side = sides[0] if sides else 'C'
        return f"{num}_{typ}_{side}.mp4"

    files = [f for f in os.listdir(folder) if f.endswith('.mp4')]
    for f in files:
        if not VALID_PATTERN.match(f):
            print(f"\n[VIDEO] 檔案名格式不正確： {f}")
            suggestion = suggest_filename(f)
            print(f"建議的新檔名： {suggestion}")
            print("選項：")
            print("1. 使用建議名")
            print("2. 自訂新檔名")
            print("3. 跳過")
            choice = input("請輸入選項（1/2/3）：").strip()
            if choice == '1':
                new_name = suggestion
            elif choice == '2':
                new_name = input("請輸入新檔名：").strip()
                if not new_name.endswith('.mp4'):
                    new_name += '.mp4'
            else:
                print("跳過。")
                continue
            # 檢查新檔名是否已存在
            if os.path.exists(os.path.join(folder, new_name)):
                print(f"目標檔名 {new_name} 已存在，無法重命名！")
                continue
            os.rename(os.path.join(folder, f), os.path.join(folder, new_name))
            print(f"已將 {f} 重命名為 {new_name}")

def check_and_rename_csvs(folder):
    # 規則：01-15_(gallery/travel/boss/museum/bowling/candy).csv
    VALID_PATTERN = re.compile(r'^(0[1-9]|1[0-5])_(gallery|travel|boss|museum|bowling|candy)\.csv$')

    def suggest_filename(filename):
        parts = re.findall(r'(\d{2}|gallery|travel|boss|museum|bowling|candy)', filename)
        nums = [p for p in parts if re.match(r'\d{2}', p)]
        types = [p for p in parts if p in ['gallery','travel','boss','museum','bowling','candy']]
        num = nums[0] if nums else '01'
        typ = types[0] if types else 'unknown'
        return f"{num}_{typ}.csv"

    files = [f for f in os.listdir(folder) if f.endswith('.csv')]
    for f in files:
        if not VALID_PATTERN.match(f):
            print(f"\n[CSV] 檔案名格式不正確： {f}")
            suggestion = suggest_filename(f)
            print(f"建議的新檔名： {suggestion}")
            print("選項：")
            print("1. 使用建議名")
            print("2. 自訂新檔名")
            print("3. 跳過")
            choice = input("請輸入選項（1/2/3）：").strip()
            if choice == '1':
                new_name = suggestion
            elif choice == '2':
                new_name = input("請輸入新檔名：").strip()
                if not new_name.endswith('.csv'):
                    new_name += '.csv'
            else:
                print("跳過。")
                continue
            # 檢查新檔名是否已存在
            if os.path.exists(os.path.join(folder, new_name)):
                print(f"目標檔名 {new_name} 已存在，無法重命名！")
                continue
            os.rename(os.path.join(folder, f), os.path.join(folder, new_name))
            print(f"已將 {f} 重命名為 {new_name}")

def main():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    VIDEO_DIR = os.path.join(BASE_DIR, 'videos')
    CSV_DIR = os.path.join(BASE_DIR, 'csvs')

    print("==== 文件名檢查與重命名工具 ====\n")
    while True:
        print("\n請選擇要執行的操作：")
        print("1. 檢查並重命名 videos（videos 子資料夾）")
        print("2. 檢查並重命名 csvs（csvs 子資料夾）")
        print("q. 退出")
        choice = input("請輸入選項（1/2/q）：").strip().lower()
        if choice == '1':
            if not os.path.exists(VIDEO_DIR):
                print(f"找不到 videos 資料夾 ({VIDEO_DIR})")
                continue
            check_and_rename_videos(VIDEO_DIR)
            print("\nDone checking videos!")
        elif choice == '2':
            if not os.path.exists(CSV_DIR):
                print(f"找不到 csvs 資料夾 ({CSV_DIR})")
                continue
            check_and_rename_csvs(CSV_DIR)
            print("\nDone checking csvs!")
        elif choice == 'q':
            print("\n退出程式。")
            break
        else:
            print("無效選項，請重新輸入。")

if __name__ == '__main__':
    main()