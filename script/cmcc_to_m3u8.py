import json
import re
import requests
from datetime import datetime, timezone, timedelta

def append_telecom_add_to_m3u8(udpxy_m3u8_file):
    """
    将 home/telecom_add.m3u8 的内容追加到指定的 M3U8 文件末尾。
    
    :param udpxy_m3u8_file: generateUdpxyM3U8 生成的目标文件路径（如 'telecom.m3u8'）
    """
    
    add_file = "./home/cmcc_add.m3u8"
    #add_file = "./cmcc_add.m3u8"
    
    try:
        with open(add_file, "r", encoding="utf-8") as f_add:
            extra_content = f_add.read()
        
        if not extra_content.strip():
            print(f"⚠️  {add_file} 为空，跳过追加。")
            return

        with open(udpxy_m3u8_file, "a", encoding="utf-8") as f_out:
            # 确保主文件末尾有换行，避免合并行
            f_out.write("\n")
            f_out.write(extra_content.rstrip("\n") + "\n")  # 避免多余空行，但保留最后一行换行
        
        print(f"✅ 已成功将 {add_file} 内容追加到 {udpxy_m3u8_file}")
    
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
    except Exception as e:
        print(f"⚠️ 追加过程中出错: {e}")

def extract_channels_to_text():
    # 1. 读取 JSON 文件
    input_filename = 'https://epg.gotonas.com/cmcc_channel.json'
    #output_filename = 'cmcc_channel.m3u8'
    output_filename = './home/udpxy_cmcc_iptv.m3u8'
    epg_file = 'https://epg.gotonas.com/t.xml.gz'
    logo_url = 'https://tv.gotonas.com/logo/'
    catchup_source = 'http://zxhk.scmcc.sctv.com:8089/yst.lookback.scmobile.com/223.87.21.116:8080/ysten-business/lookback/channel_uid/${(b)yyyyMMddHHmmss}/${(e)yyyyMMddHHmmss}/1.m3u8'
    upd_ip = 'http://192.168.100.1:4022/udp/'
    group_map = {
        "CCTV": ["CCTV", "央视"],
        "卫视": ["卫视"],
        "四川": ["四川", "SC", "CD", "成都", "峨眉"]
    }
    
    try:
        # 发送 GET 请求获取网页内容
        # timeout=10 表示 10 秒没反应就放弃，防止程序卡死
        response = requests.get(input_filename, timeout=10) 
        
        # 检查请求是否成功 (状态码 200 代表成功)
        response.raise_for_status() 
        
        # 将获取到的文本内容解析为 JSON 格式
        json_data = response.json() 
        
        print(f"成功从网络加载 {len(json_data)} 个频道数据。")
    except requests.RequestException as e:
        # 捕获所有网络相关的错误（如无法连接、超时、404等）
        print(f"网络请求错误：{e}")
        return
    except json.JSONDecodeError as e:
        # 捕获 JSON 格式解析错误
        print(f"JSON 解析错误：{e}")
        return

    # 2. 准备输出内容
    output_lines = []
    UTC8 = timezone(timedelta(hours=8))
    # 写入头
    header = f'#EXTM3U name="四川移动IPTV - {datetime.now(UTC8).strftime("%Y-%m-%d %H:%M:%S")}" x-tvg-url="{epg_file}"'
    output_lines.append(header)

    # 【新增】3. 按照 index 字段进行数字大小升序排序
    # 注意：因为 index 是字符串，必须用 int() 转换，否则 "10" 会排在 "2" 前面
    try:
        json_data.sort(key=lambda x: int(x.get('index', 0)))
        print("频道数据已按 Index 升序排序。")
    except ValueError as e:
        print(f"警告：Index 字段包含非数字内容，排序可能不准确。错误信息: {e}")

    # 4. 遍历排序后的数据并处理
    for item in json_data:
        # 提取基础字段
        index = item.get('index', 'N/A')
        uuid = item.get('uuid', 'N/A')
        channel_icon = item.get('channelIcon', '')
        channel_name = item.get('channelName', '未知频道')
        live_url = item.get('livePlayUrl', '') 

        # 提取 rtp:// 或 rtp://@ 后面的 IP 和端口部分 (到 ? 之前)
        rtp_match = re.search(r'rtp://@?([^?]+)', str(live_url))
        rtp_base = rtp_match.group(1) if rtp_match else str(live_url)
        tvg_id_match = re.search(r'logo/(.+?)\.', channel_icon)
        tvg_id = tvg_id_match.group(1) if tvg_id_match else channel_name

        tvg_id_upper = tvg_id.upper()
        channel_name_upper = channel_name.upper()
        group = next(
            (g for g, keywords in group_map.items() if any(kw in tvg_id_upper or kw in channel_name_upper for kw in keywords)), 
            "其他"
        )
        
        clean_uuid = uuid.removeprefix("ysten-")
        catchup_source_new = catchup_source.replace("channel_uid", clean_uuid)

        output_lines.append('#KODIPROP:inputstream=inputstream.ffmpegdirect')
        
        # 将字段组合成一行
        line = f'#EXTINF:-1 tvg-logo="{logo_url}{tvg_id}.png" tvg-id="{tvg_id}" tvg-name="{channel_name}" catchup="default" catchup-days="5" catchup-source="{catchup_source_new}" group-title="{group}",{channel_name}'
        output_lines.append(line)
        
        line = upd_ip + rtp_base.split("rtp://")[-1]
        output_lines.append(line)

    # 5. 写入文本文件并打印
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    append_telecom_add_to_m3u8(output_filename)
    
    print(f"成功生成提取文件：{output_filename}")
    print("\n预览前 5 行数据：")
    for i in range(min(5, len(output_lines))):
        print(output_lines[i])



if __name__ == '__main__':
    extract_channels_to_text()
	