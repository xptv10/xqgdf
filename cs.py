import requests
import re
import random
import os
import subprocess
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_ffprobe_info(url):
    command = [
        'ffprobe', '-print_format', 'json', '-show_format', '-show_streams',
        '-v', 'quiet', url
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        output = result.stdout
        data = json.loads(output)
        video_streams = data.get('streams', [])
        if video_streams:
            stream = video_streams[0]
            width = stream.get('width', 0)
            height = stream.get('height', 0)
            frame_rate = eval(stream.get('r_frame_rate', '0/0').replace('/', '.'))
            return width, height, frame_rate
        else:
            return 0, 0, 0
    except subprocess.TimeoutExpired:
        print("Error: ffprobe执行超时", flush=True)
        return 0, 0, 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return 0, 0, 0

def download_m3u8(url):
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            m3u8_content = response.text
            ts_urls = [line.strip() for line in m3u8_content.split('\n') if line and not line.startswith('#')]

            if not ts_urls:
                print("Error: 没有找到任何TS文件链接", flush=True)
                return 0

            total_size = 0
            start_time = time.time()
            ts_timeout = 15  # 设置每个.ts文件下载的超时阈值（秒）
            for ts_url in ts_urls:
                if (time.time() - start_time) > 30:
                    print("Error: 总下载时间超过30秒，判定速度不合格", flush=True)
                    return 0

                if ts_url.startswith('http'):
                    full_ts_url = ts_url
                else:
                    base_url = url.rsplit('/', 1)[0]
                    if ts_url.startswith('/'):
                        base_url = "/".join(base_url.split('/')[:-2])
                    full_ts_url = base_url + '/' + ts_url

                ts_response = requests.get(full_ts_url, timeout=ts_timeout)
                total_size += len(ts_response.content)

            end_time = time.time()
            download_time = end_time - start_time
            if download_time == 0:
                print("Error: 下载时间计算为0，不能计算下载速度", flush=True)
                return 0

            speed = total_size / (download_time * 1024)  # 计算速度，单位为KB/s
            return speed
        else:
            print(f"Error: 下载.m3u8文件失败, 状态码: {response.status_code}", flush=True)
            return 0
    except requests.exceptions.RequestException as e:
        print("HTTP请求错误:", e, flush=True)
        return 0
    except Exception as e:
        print("Error:", e, flush=True)
        return 0

def is_multicast_url(url):
    return re.search(r'udp|rtp', url, re.I)

def process_domain(domain, cctv_links, all_links):
    if not cctv_links:
        print(f"域 {domain} 下没有找到任何 CCTV 相关的链接，跳过。")
        return None, domain

    random.shuffle(cctv_links)
    selected_link = cctv_links[0]

    speed = download_m3u8(selected_link)
    width, height, frame_rate = get_ffprobe_info(selected_link)
    if speed > 0:
        print(f"频道链接 {selected_link} 在域 {domain} 下的下载速度为：{speed:.2f} KB/s")
        print(f"分辨率为：{width}x{height}，帧率为：{frame_rate}")
        genre = "genre"  # 替换为实际的类型信息
        result = [f"秒换台{speed:.2f},#{genre}#"]
        result.extend(f"{name},{url}" for name, url in all_links)
        return result, domain
    else:
        print(f"频道链接 {selected_link} 在域 {domain} 下未通过速度测试,下载速度为：{speed:.2f} KB/s。")
        print(f"分辨率为：{width}x{height}，帧率为：{frame_rate}")
        return None, domain

def process_ip_addresses(ip_data):
    print(f"正在处理数据：{ip_data}", flush=True)

    channels_info = []
    lines = ip_data.strip().split('\n')
    for line in lines:
        if ',' in line:
            channel_name, m3u8_link = line.split(',', 1)
            channels_info.append((channel_name.strip(), m3u8_link.strip()))

    if not channels_info:
        print(f"处理数据时没有找到有效的频道，跳过测速。")
        return []

    domain_dict = {}
    for name, link in channels_info:
        match = re.search(r'https?://([^/]+)/', link)
        if match:
            domain = match.group(1)
            if domain not in domain_dict:
                domain_dict[domain] = []
            domain_dict[domain].append((name, link))
        else:
            print(f"链接 {link} 无法提取域名，跳过。")

    valid_urls = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_domain = {
            executor.submit(process_domain, domain, [link for name, link in links if "CCTV" in name], links): domain for
            domain, links in domain_dict.items()}

        for future in as_completed(future_to_domain):
            result, domain = future.result()
            if result:
                valid_urls.extend(result)

    return valid_urls

# 修改后的文件路径
input_file_path = "iptv.txt"
output_file_path = "qgdf.txt"

# 从当前目录加载IP数据
with open(input_file_path, "r", encoding="utf-8") as file:
    ip_data = file.read()



# 处理文件读取的数据
result = process_ip_addresses(ip_data)

intro_content = """

秒换台5333.93,#genre#
CCTV1,http://175.18.189.238:9902/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://175.18.189.238:9902/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://175.18.189.238:9902/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://175.18.189.238:9902/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://175.18.189.238:9902/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://175.18.189.238:9902/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://175.18.189.238:9902/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://175.18.189.238:9902/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://175.18.189.238:9902/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://175.18.189.238:9902/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://175.18.189.238:9902/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://175.18.189.238:9902/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://175.18.189.238:9902/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14少儿,http://175.18.189.238:9902/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15音乐,http://175.18.189.238:9902/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV16奥林匹克,http://175.18.189.238:9902/tsfile/live/1061_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV17军农,http://175.18.189.238:9902/tsfile/live/1042_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+赛事,http://175.18.189.238:9902/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://175.18.189.238:9902/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://175.18.189.238:9902/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://175.18.189.238:9902/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://175.18.189.238:9902/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://175.18.189.238:9902/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://175.18.189.238:9902/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://175.18.189.238:9902/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://175.18.189.238:9902/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://175.18.189.238:9902/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://175.18.189.238:9902/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://175.18.189.238:9902/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://175.18.189.238:9902/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
山西卫视,http://175.18.189.238:9902/tsfile/live/0118_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://175.18.189.238:9902/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://175.18.189.238:9902/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://175.18.189.238:9902/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://175.18.189.238:9902/tsfile/live/0117_2.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://175.18.189.238:9902/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://175.18.189.238:9902/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://175.18.189.238:9902/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
海南卫视,http://175.18.189.238:9902/tsfile/live/0114_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://175.18.189.238:9902/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://175.18.189.238:9902/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://175.18.189.238:9902/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://175.18.189.238:9902/tsfile/live/0119_2.m3u8?key=txiptv&playlive=1&authid=0
西藏卫视,http://175.18.189.238:9902/tsfile/live/0111_1.m3u8?key=txiptv&playlive=1&authid=0
陕西卫视,http://175.18.189.238:9902/tsfile/live/0136_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://175.18.189.238:9902/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
兵团卫视,http://175.18.189.238:9902/tsfile/live/0115_1.m3u8?key=txiptv&playlive=1&authid=0
甘肃卫视,http://175.18.189.238:9902/tsfile/live/0141_1.m3u8?key=txiptv&playlive=1&authid=0
新疆卫视,http://175.18.189.238:9902/tsfile/live/0110_1.m3u8?key=txiptv&playlive=1&authid=0
宁夏卫视,http://175.18.189.238:9902/tsfile/live/0112_1.m3u8?key=txiptv&playlive=1&authid=0
内蒙古卫视,http://175.18.189.238:9902/tsfile/live/0109_1.m3u8?key=txiptv&playlive=1&authid=0
吉林公共,http://175.18.189.238:9902/tsfile/live/1001_1.m3u8?key=txiptv&playlive=1&authid=0
吉林都市,http://175.18.189.238:9902/tsfile/live/1002_1.m3u8?key=txiptv&playlive=1&authid=0
吉林7,http://175.18.189.238:9902/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
东北戏曲,http://175.18.189.238:9902/tsfile/live/1072_1.m3u8?key=txiptv&playlive=1&authid=0
吉林影视,http://175.18.189.238:9902/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0
吉林生活,http://175.18.189.238:9902/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
吉林乡村,http://175.18.189.238:9902/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
长影,http://175.18.189.238:9902/tsfile/live/1010_1.m3u8?key=txiptv&playlive=1&authid=0
吉林教育,http://175.18.189.238:9902/tsfile/live/1004_1.m3u8?key=txiptv&playlive=1&authid=0
延边卫视,http://175.18.189.238:9902/tsfile/live/1011_1.m3u8?key=txiptv&playlive=1&authid=0
松原,http://175.18.189.238:9902/tsfile/live/1012_1.m3u8?key=txiptv&playlive=1&authid=0
松原公共,http://175.18.189.238:9902/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0
CHC动作电影,http://175.18.189.238:9902/tsfile/live/1014_1.m3u8?key=txiptv&playlive=1&authid=0
CHC电影,http://175.18.189.238:9902/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0
CHC家庭影院,http://175.18.189.238:9902/tsfile/live/1016_1.m3u8?key=txiptv&playlive=1&authid=0
体育赛事,http://175.18.189.238:9902/tsfile/live/1017_1.m3u8?key=txiptv&playlive=1&authid=0
极速汽车,http://175.18.189.238:9902/tsfile/live/1018_1.m3u8?key=txiptv&playlive=1&authid=0
游戏风云,http://175.18.189.238:9902/tsfile/live/1019_1.m3u8?key=txiptv&playlive=1&authid=0
动漫秀场,http://175.18.189.238:9902/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0
生活时尚,http://175.18.189.238:9902/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0
都市时尚,http://175.18.189.238:9902/tsfile/live/1022_1.m3u8?key=txiptv&playlive=1&authid=0
金色,http://175.18.189.238:9902/tsfile/live/1023_1.m3u8?key=txiptv&playlive=1&authid=0
法制天地,http://175.18.189.238:9902/tsfile/live/1024_1.m3u8?key=txiptv&playlive=1&authid=0
第一剧场,http://175.18.189.238:9902/tsfile/live/1025_1.m3u8?key=txiptv&playlive=1&authid=0
怀旧剧场,http://175.18.189.238:9902/tsfile/live/1026_1.m3u8?key=txiptv&playlive=1&authid=0
电视指南,http://175.18.189.238:9902/tsfile/live/1027_1.m3u8?key=txiptv&playlive=1&authid=0
央视文化精品,http://175.18.189.238:9902/tsfile/live/1028_1.m3u8?key=txiptv&playlive=1&authid=0
地理世界,http://175.18.189.238:9902/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0
兵器科技,http://175.18.189.238:9902/tsfile/live/1030_1.m3u8?key=txiptv&playlive=1&authid=0
女性时尚,http://175.18.189.238:9902/tsfile/live/1031_1.m3u8?key=txiptv&playlive=1&authid=0
风云音乐,http://175.18.189.238:9902/tsfile/live/1032_1.m3u8?key=txiptv&playlive=1&authid=0
风云足球,http://175.18.189.238:9902/tsfile/live/1033_1.m3u8?key=txiptv&playlive=1&authid=0
风云剧场,http://175.18.189.238:9902/tsfile/live/1034_1.m3u8?key=txiptv&playlive=1&authid=0
央视台球,http://175.18.189.238:9902/tsfile/live/1035_1.m3u8?key=txiptv&playlive=1&authid=0
卫生健康,http://175.18.189.238:9902/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0
高尔夫,http://175.18.189.238:9902/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0
中国交通,http://175.18.189.238:9902/tsfile/live/1038_1.m3u8?key=txiptv&playlive=1&authid=0
CETV1,http://175.18.189.238:9902/tsfile/live/1039_1.m3u8?key=txiptv&playlive=1&authid=0
CETV2,http://175.18.189.238:9902/tsfile/live/1009_1.m3u8?key=txiptv&playlive=1&authid=0
CETV4,http://175.18.189.238:9902/tsfile/live/1052_1.m3u8?key=txiptv&playlive=1&authid=0
上海纪实,http://175.18.189.238:9902/tsfile/live/1040_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰纪实,http://175.18.189.238:9902/tsfile/live/1041_1.m3u8?key=txiptv&playlive=1&authid=0
BTV,http://175.18.189.238:9902/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0
卡酷动画,http://175.18.189.238:9902/tsfile/live/1043_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰卡通,http://175.18.189.238:9902/tsfile/live/1044_1.m3u8?key=txiptv&playlive=1&authid=0
哈哈炫动,http://175.18.189.238:9902/tsfile/live/1045_1.m3u8?key=txiptv&playlive=1&authid=0
嘉佳卡通,http://175.18.189.238:9902/tsfile/live/1046_1.m3u8?key=txiptv&playlive=1&authid=0
老故事,http://175.18.189.238:9902/tsfile/live/1047_1.m3u8?key=txiptv&playlive=1&authid=0
国学,http://175.18.189.238:9902/tsfile/live/1048_1.m3u8?key=txiptv&playlive=1&authid=0
环球奇观,http://175.18.189.238:9902/tsfile/live/1049_1.m3u8?key=txiptv&playlive=1&authid=0
汽摩,http://175.18.189.238:9902/tsfile/live/1050_1.m3u8?key=txiptv&playlive=1&authid=0
靓妆,http://175.18.189.238:9902/tsfile/live/1051_1.m3u8?key=txiptv&playlive=1&authid=0
快乐垂钓,http://175.18.189.238:9902/tsfile/live/1054_1.m3u8?key=txiptv&playlive=1&authid=0
茶,http://175.18.189.238:9902/tsfile/live/1056_1.m3u8?key=txiptv&playlive=1&authid=0





秒换台7449.34,#genre#
CCTV1,http://58.19.38.162:9901/tsfile/live/1000_1.m3u8
CCTV2,http://58.19.38.162:9901/tsfile/live/1001_1.m3u8
CCTV3,http://58.19.38.162:9901/tsfile/live/1002_1.m3u8
CCTV4,http://58.19.38.162:9901/tsfile/live/1003_1.m3u8
CCTV5,http://58.19.38.162:9901/tsfile/live/1004_1.m3u8
CCTV5+,http://58.19.38.162:9901/tsfile/live/1014_1.m3u8
CCTV6,http://58.19.38.162:9901/tsfile/live/1005_1.m3u8
CCTV7,http://58.19.38.162:9901/tsfile/live/1006_1.m3u8
CCTV8,http://58.19.38.162:9901/tsfile/live/1007_1.m3u8
CCTV9,http://58.19.38.162:9901/tsfile/live/1008_1.m3u8
CCTV10,http://58.19.38.162:9901/tsfile/live/1009_1.m3u8
CCTV11,http://58.19.38.162:9901/tsfile/live/1010_1.m3u8
CCTV12,http://58.19.38.162:9901/tsfile/live/1011_1.m3u8
CCTV13,http://58.19.38.162:9901/tsfile/live/1012_1.m3u8
CCTV14,http://58.19.38.162:9901/tsfile/live/1013_1.m3u8
CCTV15,http://58.19.38.162:9901/tsfile/live/0015_1.m3u8
CHC动作电影,http://58.19.38.162:9901/tsfile/live/1037_1.m3u8
CHC家庭影院,http://58.19.38.162:9901/tsfile/live/1036_1.m3u8
CHC电影,http://58.19.38.162:9901/tsfile/live/1038_1.m3u8
上海卫视,http://58.19.38.162:9901/tsfile/live/1018_1.m3u8
东南卫视,http://58.19.38.162:9901/tsfile/live/1028_1.m3u8
北京卫视,http://58.19.38.162:9901/tsfile/live/1017_1.m3u8
天津卫视,http://58.19.38.162:9901/tsfile/live/1024_1.m3u8
安徽卫视,http://58.19.38.162:9901/tsfile/live/1021_1.m3u8
山东卫视,http://58.19.38.162:9901/tsfile/live/1025_1.m3u8
广东卫视,http://58.19.38.162:9901/tsfile/live/1022_1.m3u8
江苏卫视,http://58.19.38.162:9901/tsfile/live/1019_1.m3u8
江西卫视,http://58.19.38.162:9901/tsfile/live/1029_1.m3u8
河南卫视,http://58.19.38.162:9901/tsfile/live/1026_1.m3u8
浙江卫视,http://58.19.38.162:9901/tsfile/live/1020_1.m3u8
深圳卫视,http://58.19.38.162:9901/tsfile/live/1023_1.m3u8
湖北卫视,http://58.19.38.162:9901/tsfile/live/1015_1.m3u8
湖南卫视,http://58.19.38.162:9901/tsfile/live/1016_1.m3u8
贵州卫视,http://58.19.38.162:9901/tsfile/live/1030_1.m3u8
辽宁卫视,http://58.19.38.162:9901/tsfile/live/1027_1.m3u8

秒换台1,#genre#
cctv1,http://119.163.199.98:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
cctv2,http://119.163.199.98:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
cctv3,http://119.163.199.98:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
cctv4,http://119.163.199.98:9901/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
cctv5,http://119.163.199.98:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
cctv6,http://119.163.199.98:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
cctv7,http://119.163.199.98:9901/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
cctv8,http://119.163.199.98:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
cctv9,http://119.163.199.98:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
cctv10,http://119.163.199.98:9901/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
cctv11,http://119.163.199.98:9901/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
cctv12,http://119.163.199.98:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
cctv13,http://119.163.199.98:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
cctv14,http://119.163.199.98:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
cctv15,http://119.163.199.98:9901/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
cctv5+体育赛事,http://119.163.199.98:9901/tsfile/live/0016_2.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://119.163.199.98:9901/tsfile/live/0017_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://119.163.199.98:9901/tsfile/live/0018_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://119.163.199.98:9901/tsfile/live/0019_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://119.163.199.98:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://119.163.199.98:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://119.163.199.98:9901/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://119.163.199.98:9901/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://119.163.199.98:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://119.163.199.98:9901/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://119.163.199.98:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://119.163.199.98:9901/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://119.163.199.98:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://119.163.199.98:9901/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://119.163.199.98:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://119.163.199.98:9901/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://119.163.199.98:9901/tsfile/live/0113_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://119.163.199.98:9901/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://119.163.199.98:9901/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://119.163.199.98:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://119.163.199.98:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://119.163.199.98:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://119.163.199.98:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://119.163.199.98:9901/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0
山东体育,http://119.163.199.98:9901/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://119.163.199.98:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0

秒换台3183.27,#genre#
CCTV1,http://111.225.115.176:808/home/storager/6bbc84c2-18fb-444e-a900-d7ed884a2731/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://111.225.115.176:808/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://111.225.115.176:808/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://111.225.115.176:808/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://111.225.115.176:808/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://111.225.115.176:808/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://111.225.115.176:808/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://111.225.115.176:808/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://111.225.115.176:808/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://111.225.115.176:808/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://111.225.115.176:808/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://111.225.115.176:808/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://111.225.115.176:808/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14,http://111.225.115.176:808/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15,http://111.225.115.176:808/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV17,http://111.225.115.176:808/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+,http://111.225.115.176:808/tsfile/live/0017_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://111.225.115.176:808/tsfile/live/0018_1.m3u8?key=txiptv&playlive=1&authid=0
河北经济生活,http://111.225.115.176:808/tsfile/live/0019_1.m3u8?key=txiptv&playlive=1&authid=0
河北都市,http://111.225.115.176:808/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0
河北影视剧,http://111.225.115.176:808/tsfile/live/1001_1.m3u8?key=txiptv&playlive=1&authid=0
河北少儿科教,http://111.225.115.176:808/tsfile/live/1002_1.m3u8?key=txiptv&playlive=1&authid=0
河北公共,http://111.225.115.176:808/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
河北农民,http://111.225.115.176:808/tsfile/live/1004_1.m3u8?key=txiptv&playlive=1&authid=0
河北杂技,http://111.225.115.176:808/tsfile/live/1005_1.m3u8?key=txiptv&playlive=1&authid=0
保定新闻综合,http://111.225.115.176:808/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0
保定公共,http://111.225.115.176:808/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
保定生活健康,http://111.225.115.176:808/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://111.225.115.176:808/tsfile/live/1009_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://111.225.115.176:808/tsfile/live/1010_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://111.225.115.176:808/tsfile/live/1011_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://111.225.115.176:808/tsfile/live/1012_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://111.225.115.176:808/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://111.225.115.176:808/tsfile/live/1014_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://111.225.115.176:808/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://111.225.115.176:808/tsfile/live/1016_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://111.225.115.176:808/tsfile/live/1017_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://111.225.115.176:808/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://111.225.115.176:808/tsfile/live/1018_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://111.225.115.176:808/tsfile/live/1019_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://111.225.115.176:808/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://111.225.115.176:808/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://111.225.115.176:808/tsfile/live/1022_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://111.225.115.176:808/tsfile/live/1023_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://111.225.115.176:808/tsfile/live/1024_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://111.225.115.176:808/tsfile/live/1025_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://111.225.115.176:808/tsfile/live/1026_1.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://111.225.115.176:808/tsfile/live/1027_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://111.225.115.176:808/tsfile/live/0113_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://111.225.115.176:808/tsfile/live/1028_1.m3u8?key=txiptv&playlive=1&authid=0
陕西卫视,http://111.225.115.176:808/tsfile/live/0136_1.m3u8?key=txiptv&playlive=1&authid=0
内蒙古卫视,http://111.225.115.176:808/tsfile/live/0109_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://111.225.115.176:808/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
海南卫视,http://111.225.115.176:808/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0
宁夏卫视,http://111.225.115.176:808/tsfile/live/0112_1.m3u8?key=txiptv&playlive=1&authid=0
西藏卫视,http://111.225.115.176:808/tsfile/live/0111_1.m3u8?key=txiptv&playlive=1&authid=0
新疆卫视,http://111.225.115.176:808/tsfile/live/0110_1.m3u8?key=txiptv&playlive=1&authid=0
山东教育,http://111.225.115.176:808/tsfile/live/1030_1.m3u8?key=txiptv&playlive=1&authid=0
纪实人文,http://111.225.115.176:808/tsfile/live/1033_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰卡通,http://111.225.115.176:808/tsfile/live/1031_1.m3u8?key=txiptv&playlive=1&authid=0
CETV1,http://111.225.115.176:808/tsfile/live/1034_1.m3u8?key=txiptv&playlive=1&authid=0
BTV冬奥纪实,http://111.225.115.176:808/tsfile/live/1035_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰纪实,http://111.225.115.176:808/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0
CETV2,http://111.225.115.176:808/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0
CETV4,http://111.225.115.176:808/tsfile/live/1038_1.m3u8?key=txiptv&playlive=1&authid=0
中国交通,http://111.225.115.176:808/tsfile/live/1039_1.m3u8?key=txiptv&playlive=1&authid=0
秒换台2382.66,#genre#
CCTV1,http://119.62.36.174:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV2,http://119.62.36.174:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV3,http://119.62.36.174:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV4,http://119.62.36.174:9901/tsfile/live/0004_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV5,http://119.62.36.174:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV6,http://119.62.36.174:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV7,http://119.62.36.174:9901/tsfile/live/0007_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV8,http://119.62.36.174:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV9,http://119.62.36.174:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV10,http://119.62.36.174:9901/tsfile/live/0010_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV11,http://119.62.36.174:9901/tsfile/live/0011_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV12,http://119.62.36.174:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV13,http://119.62.36.174:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV14,http://119.62.36.174:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=0&authid=0
CCTV15,http://119.62.36.174:9901/tsfile/live/0015_1.m3u8?key=txiptv&playlive=0&authid=0
都市,http://119.62.36.174:9901/tsfile/live/0128_1.m3u8?key=txiptv&playlive=0&authid=0
娱乐,http://119.62.36.174:9901/tsfile/live/0124_1.m3u8?key=txiptv&playlive=0&authid=0
公共,http://119.62.36.174:9901/tsfile/live/0127_1.m3u8?key=txiptv&playlive=0&authid=0
浙江卫视,http://119.62.36.174:9901/tsfile/live/0127_2.m3u8?key=txiptv&playlive=0&authid=0
江苏卫视,http://119.62.36.174:9901/tsfile/live/0130_1.m3u8?key=txiptv&playlive=0&authid=0
湖南卫视,http://119.62.36.174:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=0&authid=0
东方卫视,http://119.62.36.174:9901/tsfile/live/0135_2.m3u8?key=txiptv&playlive=0&authid=0
北京卫视,http://119.62.36.174:9901/tsfile/live/0135_1.m3u8?key=txiptv&playlive=0&authid=0
天津卫视,http://119.62.36.174:9901/tsfile/live/0138_1.m3u8?key=txiptv&playlive=0&authid=0
安徽卫视,http://119.62.36.174:9901/tsfile/live/0126_1.m3u8?key=txiptv&playlive=0&authid=0
深圳卫视,http://119.62.36.174:9901/tsfile/live/0142_1.m3u8?key=txiptv&playlive=0&authid=0
重庆卫视,http://119.62.36.174:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=0&authid=0
山东卫视,http://119.62.36.174:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=0&authid=0
辽宁卫视,http://119.62.36.174:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=0&authid=0
湖北卫视,http://119.62.36.174:9901/tsfile/live/0123_1.m3u8?key=txiptv&playlive=0&authid=0
四川卫视,http://119.62.36.174:9901/tsfile/live/0139_2.m3u8?key=txiptv&playlive=0&authid=0
黑龙江卫视,http://119.62.36.174:9901/tsfile/live/0138_2.m3u8?key=txiptv&playlive=0&authid=0
东南卫视,http://119.62.36.174:9901/tsfile/live/0120_1.m3u8?key=txiptv&playlive=0&authid=0
贵州卫视,http://119.62.36.174:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=0&authid=0
广东卫视,http://119.62.36.174:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=0&authid=0
河南卫视,http://119.62.36.174:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=0&authid=0
吉林卫视,http://119.62.36.174:9901/tsfile/live/0118_1.m3u8?key=txiptv&playlive=0&authid=0
山西卫视,http://119.62.36.174:9901/tsfile/live/0136_1.m3u8?key=txiptv&playlive=0&authid=0
河北卫视,http://119.62.36.174:9901/tsfile/live/0113_1.m3u8?key=txiptv&playlive=0&authid=0
广西卫视,http://119.62.36.174:9901/tsfile/live/0109_1.m3u8?key=txiptv&playlive=0&authid=0
陕西卫视,http://119.62.36.174:9901/tsfile/live/0140_1.m3u8?key=txiptv&playlive=0&authid=0
甘肃卫视,http://119.62.36.174:9901/tsfile/live/0141_1.m3u8?key=txiptv&playlive=0&authid=0
青海卫视,http://119.62.36.174:9901/tsfile/live/0112_1.m3u8?key=txiptv&playlive=0&authid=0
内蒙古卫视,http://119.62.36.174:9901/tsfile/live/0109_2.m3u8?key=txiptv&playlive=0&authid=0
海南卫视,http://119.62.36.174:9901/tsfile/live/1003_1.m3u8?key=txiptv&playlive=0&authid=0
厦门卫视,http://119.62.36.174:9901/tsfile/live/0115_1.m3u8?key=txiptv&playlive=0&authid=0
金鹰卡通,http://119.62.36.174:9901/tsfile/live/1005_1.m3u8?key=txiptv&playlive=0&authid=0
优漫卡通,http://119.62.36.174:9901/tsfile/live/1007_1.m3u8?key=txiptv&playlive=0&authid=0
嘉佳卡通,http://119.62.36.174:9901/tsfile/live/1008_1.m3u8?key=txiptv&playlive=0&authid=0
哈哈炫动,http://119.62.36.174:9901/tsfile/live/1009_1.m3u8?key=txiptv&playlive=0&authid=0
北京卡通,http://119.62.36.174:9901/tsfile/live/1010_1.m3u8?key=txiptv&playlive=0&authid=0
秒换台5280.58,#genre#
CCTV1,http://111.225.113.214:808/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://111.225.113.214:808/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://111.225.113.214:808/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://111.225.113.214:808/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://111.225.113.214:808/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://111.225.113.214:808/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://111.225.113.214:808/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://111.225.113.214:808/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://111.225.113.214:808/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://111.225.113.214:808/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://111.225.113.214:808/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://111.225.113.214:808/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://111.225.113.214:808/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14,http://111.225.113.214:808/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15,http://111.225.113.214:808/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV16,http://111.225.113.214:808/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV17,http://111.225.113.214:808/tsfile/live/0017_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+,http://111.225.113.214:808/tsfile/live/0018_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://111.225.113.214:808/tsfile/live/0019_1.m3u8?key=txiptv&playlive=1&authid=0
河北经济生活,http://111.225.113.214:808/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0
河北都市,http://111.225.113.214:808/tsfile/live/1001_1.m3u8?key=txiptv&playlive=1&authid=0
河北影视剧,http://111.225.113.214:808/tsfile/live/1002_1.m3u8?key=txiptv&playlive=1&authid=0
河北少儿科教,http://111.225.113.214:808/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
河北公共,http://111.225.113.214:808/tsfile/live/1004_1.m3u8?key=txiptv&playlive=1&authid=0
河北农民,http://111.225.113.214:808/tsfile/live/1005_1.m3u8?key=txiptv&playlive=1&authid=0
河北杂技,http://111.225.113.214:808/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0
保定新闻综合,http://111.225.113.214:808/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
保定公共,http://111.225.113.214:808/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
保定生活健康,http://111.225.113.214:808/tsfile/live/1009_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://111.225.113.214:808/tsfile/live/1010_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://111.225.113.214:808/tsfile/live/1011_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://111.225.113.214:808/tsfile/live/1012_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://111.225.113.214:808/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://111.225.113.214:808/tsfile/live/1014_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://111.225.113.214:808/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://111.225.113.214:808/tsfile/live/1016_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://111.225.113.214:808/tsfile/live/1017_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://111.225.113.214:808/tsfile/live/1018_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://111.225.113.214:808/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://111.225.113.214:808/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
内蒙古卫视,http://111.225.113.214:808/tsfile/live/0109_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://111.225.113.214:808/tsfile/live/1019_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://111.225.113.214:808/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://111.225.113.214:808/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://111.225.113.214:808/tsfile/live/1022_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://111.225.113.214:808/tsfile/live/1023_1.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://111.225.113.214:808/tsfile/live/1024_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://111.225.113.214:808/tsfile/live/0113_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://111.225.113.214:808/tsfile/live/1025_1.m3u8?key=txiptv&playlive=1&authid=0
海南卫视,http://111.225.113.214:808/tsfile/live/1026_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰卡通,http://111.225.113.214:808/tsfile/live/1027_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰纪实,http://111.225.113.214:808/tsfile/live/1028_1.m3u8?key=txiptv&playlive=1&authid=0
CETV2,http://111.225.113.214:808/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0
CETV4,http://111.225.113.214:808/tsfile/live/1030_1.m3u8?key=txiptv&playlive=1&authid=0
中国交通,http://111.225.113.214:808/tsfile/live/1031_1.m3u8?key=txiptv&playlive=1&authid=0
武术世界,http://111.225.113.214:808/tsfile/live/1032_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV第一剧场,http://111.225.113.214:808/tsfile/live/1033_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV风云剧场,http://111.225.113.214:808/tsfile/live/1034_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV怀旧剧场,http://111.225.113.214:808/tsfile/live/1035_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV风云音乐,http://111.225.113.214:808/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV风云足球,http://111.225.113.214:808/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0
秒换台6690.51,#genre#
CCTV1,http://175.18.189.238:9902/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://175.18.189.238:9902/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://175.18.189.238:9902/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://175.18.189.238:9902/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://175.18.189.238:9902/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://175.18.189.238:9902/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://175.18.189.238:9902/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://175.18.189.238:9902/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://175.18.189.238:9902/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://175.18.189.238:9902/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://175.18.189.238:9902/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://175.18.189.238:9902/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://175.18.189.238:9902/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14少儿,http://175.18.189.238:9902/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15音乐,http://175.18.189.238:9902/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV16奥林匹克,http://175.18.189.238:9902/tsfile/live/1061_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV17军农,http://175.18.189.238:9902/tsfile/live/1042_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+赛事,http://175.18.189.238:9902/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://175.18.189.238:9902/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://175.18.189.238:9902/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://175.18.189.238:9902/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://175.18.189.238:9902/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://175.18.189.238:9902/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://175.18.189.238:9902/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://175.18.189.238:9902/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://175.18.189.238:9902/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://175.18.189.238:9902/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://175.18.189.238:9902/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://175.18.189.238:9902/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://175.18.189.238:9902/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
山西卫视,http://175.18.189.238:9902/tsfile/live/0118_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://175.18.189.238:9902/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://175.18.189.238:9902/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://175.18.189.238:9902/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://175.18.189.238:9902/tsfile/live/0117_2.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://175.18.189.238:9902/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://175.18.189.238:9902/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://175.18.189.238:9902/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
海南卫视,http://175.18.189.238:9902/tsfile/live/0114_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://175.18.189.238:9902/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://175.18.189.238:9902/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://175.18.189.238:9902/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://175.18.189.238:9902/tsfile/live/0119_2.m3u8?key=txiptv&playlive=1&authid=0
西藏卫视,http://175.18.189.238:9902/tsfile/live/0111_1.m3u8?key=txiptv&playlive=1&authid=0
陕西卫视,http://175.18.189.238:9902/tsfile/live/0136_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://175.18.189.238:9902/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
兵团卫视,http://175.18.189.238:9902/tsfile/live/0115_1.m3u8?key=txiptv&playlive=1&authid=0
甘肃卫视,http://175.18.189.238:9902/tsfile/live/0141_1.m3u8?key=txiptv&playlive=1&authid=0
新疆卫视,http://175.18.189.238:9902/tsfile/live/0110_1.m3u8?key=txiptv&playlive=1&authid=0
宁夏卫视,http://175.18.189.238:9902/tsfile/live/0112_1.m3u8?key=txiptv&playlive=1&authid=0
内蒙古卫视,http://175.18.189.238:9902/tsfile/live/0109_1.m3u8?key=txiptv&playlive=1&authid=0
吉林公共,http://175.18.189.238:9902/tsfile/live/1001_1.m3u8?key=txiptv&playlive=1&authid=0
吉林都市,http://175.18.189.238:9902/tsfile/live/1002_1.m3u8?key=txiptv&playlive=1&authid=0
吉林7,http://175.18.189.238:9902/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
东北戏曲,http://175.18.189.238:9902/tsfile/live/1072_1.m3u8?key=txiptv&playlive=1&authid=0
吉林影视,http://175.18.189.238:9902/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0
吉林生活,http://175.18.189.238:9902/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
吉林乡村,http://175.18.189.238:9902/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
长影,http://175.18.189.238:9902/tsfile/live/1010_1.m3u8?key=txiptv&playlive=1&authid=0
吉林教育,http://175.18.189.238:9902/tsfile/live/1004_1.m3u8?key=txiptv&playlive=1&authid=0
延边卫视,http://175.18.189.238:9902/tsfile/live/1011_1.m3u8?key=txiptv&playlive=1&authid=0
松原,http://175.18.189.238:9902/tsfile/live/1012_1.m3u8?key=txiptv&playlive=1&authid=0
松原公共,http://175.18.189.238:9902/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0
CHC动作电影,http://175.18.189.238:9902/tsfile/live/1014_1.m3u8?key=txiptv&playlive=1&authid=0
CHC电影,http://175.18.189.238:9902/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0
CHC家庭影院,http://175.18.189.238:9902/tsfile/live/1016_1.m3u8?key=txiptv&playlive=1&authid=0
体育赛事,http://175.18.189.238:9902/tsfile/live/1017_1.m3u8?key=txiptv&playlive=1&authid=0
极速汽车,http://175.18.189.238:9902/tsfile/live/1018_1.m3u8?key=txiptv&playlive=1&authid=0
游戏风云,http://175.18.189.238:9902/tsfile/live/1019_1.m3u8?key=txiptv&playlive=1&authid=0
动漫秀场,http://175.18.189.238:9902/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0
生活时尚,http://175.18.189.238:9902/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0
都市时尚,http://175.18.189.238:9902/tsfile/live/1022_1.m3u8?key=txiptv&playlive=1&authid=0
金色,http://175.18.189.238:9902/tsfile/live/1023_1.m3u8?key=txiptv&playlive=1&authid=0
法制天地,http://175.18.189.238:9902/tsfile/live/1024_1.m3u8?key=txiptv&playlive=1&authid=0
第一剧场,http://175.18.189.238:9902/tsfile/live/1025_1.m3u8?key=txiptv&playlive=1&authid=0
怀旧剧场,http://175.18.189.238:9902/tsfile/live/1026_1.m3u8?key=txiptv&playlive=1&authid=0
电视指南,http://175.18.189.238:9902/tsfile/live/1027_1.m3u8?key=txiptv&playlive=1&authid=0
央视文化精品,http://175.18.189.238:9902/tsfile/live/1028_1.m3u8?key=txiptv&playlive=1&authid=0
地理世界,http://175.18.189.238:9902/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0
兵器科技,http://175.18.189.238:9902/tsfile/live/1030_1.m3u8?key=txiptv&playlive=1&authid=0
女性时尚,http://175.18.189.238:9902/tsfile/live/1031_1.m3u8?key=txiptv&playlive=1&authid=0
风云音乐,http://175.18.189.238:9902/tsfile/live/1032_1.m3u8?key=txiptv&playlive=1&authid=0
风云足球,http://175.18.189.238:9902/tsfile/live/1033_1.m3u8?key=txiptv&playlive=1&authid=0
风云剧场,http://175.18.189.238:9902/tsfile/live/1034_1.m3u8?key=txiptv&playlive=1&authid=0
央视台球,http://175.18.189.238:9902/tsfile/live/1035_1.m3u8?key=txiptv&playlive=1&authid=0
卫生健康,http://175.18.189.238:9902/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0
高尔夫,http://175.18.189.238:9902/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0
中国交通,http://175.18.189.238:9902/tsfile/live/1038_1.m3u8?key=txiptv&playlive=1&authid=0
CETV1,http://175.18.189.238:9902/tsfile/live/1039_1.m3u8?key=txiptv&playlive=1&authid=0
CETV2,http://175.18.189.238:9902/tsfile/live/1009_1.m3u8?key=txiptv&playlive=1&authid=0
CETV4,http://175.18.189.238:9902/tsfile/live/1052_1.m3u8?key=txiptv&playlive=1&authid=0
上海纪实,http://175.18.189.238:9902/tsfile/live/1040_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰纪实,http://175.18.189.238:9902/tsfile/live/1041_1.m3u8?key=txiptv&playlive=1&authid=0
BTV,http://175.18.189.238:9902/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0
卡酷动画,http://175.18.189.238:9902/tsfile/live/1043_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰卡通,http://175.18.189.238:9902/tsfile/live/1044_1.m3u8?key=txiptv&playlive=1&authid=0
哈哈炫动,http://175.18.189.238:9902/tsfile/live/1045_1.m3u8?key=txiptv&playlive=1&authid=0
嘉佳卡通,http://175.18.189.238:9902/tsfile/live/1046_1.m3u8?key=txiptv&playlive=1&authid=0
老故事,http://175.18.189.238:9902/tsfile/live/1047_1.m3u8?key=txiptv&playlive=1&authid=0
国学,http://175.18.189.238:9902/tsfile/live/1048_1.m3u8?key=txiptv&playlive=1&authid=0
环球奇观,http://175.18.189.238:9902/tsfile/live/1049_1.m3u8?key=txiptv&playlive=1&authid=0
汽摩,http://175.18.189.238:9902/tsfile/live/1050_1.m3u8?key=txiptv&playlive=1&authid=0
靓妆,http://175.18.189.238:9902/tsfile/live/1051_1.m3u8?key=txiptv&playlive=1&authid=0
快乐垂钓,http://175.18.189.238:9902/tsfile/live/1054_1.m3u8?key=txiptv&playlive=1&authid=0
茶,http://175.18.189.238:9902/tsfile/live/1056_1.m3u8?key=txiptv&playlive=1&authid=0

热剧连播,#genre#
【古代战场】,
古代战场-01,https://yzzy.play-cdn12.com/20230307/20874_b1700291/index.m3u8
古代战场-02,https://yzzy.play-cdn12.com/20230307/20873_ef6e557d/index.m3u8
古代战场-03,https://yzzy.play-cdn12.com/20230307/20872_5b359014/index.m3u8
古代战场-04,https://yzzy.play-cdn12.com/20230307/20871_4fe553e4/index.m3u8
古代战场-05,https://yzzy.play-cdn12.com/20230307/20870_bf40177f/index.m3u8
古代战场-06,https://yzzy.play-cdn12.com/20230307/20869_70cdcf0f/index.m3u8
古代战场-07,https://yzzy.play-cdn12.com/20230307/20868_6dde5b22/index.m3u8
古代战场-08,https://yzzy.play-cdn12.com/20230307/20867_f2683455/index.m3u8
古代战场-09,https://yzzy.play-cdn12.com/20230307/20866_087ffdf9/index.m3u8
古代战场-10,https://yzzy.play-cdn12.com/20230307/20865_232e9de5/index.m3u8
古代战场-11,https://yzzy.play-cdn12.com/20230307/20864_de1b4592/index.m3u8
古代战场-12,https://yzzy.play-cdn12.com/20230307/20863_ed2d67e4/index.m3u8
古代战场-13,https://yzzy.play-cdn12.com/20230307/20862_979f997e/index.m3u8
古代战场-14,https://yzzy.play-cdn12.com/20230307/20861_430bf190/index.m3u8
古代战场-15,https://yzzy.play-cdn12.com/20230307/20860_32c674db/index.m3u8
古代战场-16,https://yzzy.play-cdn12.com/20230307/20859_a91f6a9b/index.m3u8
古代战场-17,https://yzzy.play-cdn12.com/20230307/20858_ff019fdd/index.m3u8
古代战场-18,https://yzzy.play-cdn12.com/20230307/20857_28e0aac6/index.m3u8
古代战场-19,https://yzzy.play-cdn12.com/20230307/20856_f59d9a0a/index.m3u8
古代战场-20,https://yzzy.play-cdn12.com/20230307/20855_402c96fe/index.m3u8
古代战场2-01,https://yzzy.play-cdn12.com/20230313/22295_747661b7/index.m3u8
古代战场2-02,https://yzzy.play-cdn12.com/20230313/22294_d794cd92/index.m3u8
古代战场2-03,https://yzzy.play-cdn12.com/20230313/22293_744300b1/index.m3u8
古代战场2-04,https://yzzy.play-cdn12.com/20230313/22292_179a87c7/index.m3u8
古代战场2-05,https://yzzy.play-cdn12.com/20230313/22291_b7eb39b5/index.m3u8
古代战场2-06,https://yzzy.play-cdn12.com/20230313/22290_65591eea/index.m3u8
古代战场2-07,https://yzzy.play-cdn12.com/20230313/22289_05292533/index.m3u8
古代战场2-08,https://yzzy.play-cdn12.com/20230313/22288_a098805c/index.m3u8
古代战场2-09,https://yzzy.play-cdn12.com/20230313/22287_6fd3ede6/index.m3u8
古代战场2-10,https://yzzy.play-cdn12.com/20230313/22286_2760594f/index.m3u8
古代战场2-11,https://yzzy.play-cdn12.com/20230313/22285_91851c19/index.m3u8
古代战场2-12,https://yzzy.play-cdn12.com/20230313/22284_018ddce5/index.m3u8
古代战场2-13,https://yzzy.play-cdn12.com/20230313/22283_4f7c896a/index.m3u8
古代战场2-14,https://yzzy.play-cdn12.com/20230313/22282_dca64b0d/index.m3u8
古代战场2-15,https://vip15.play-cdn15.com/20230321/3485_a507c64c/index.m3u8
古代战场2-16,https://vip15.play-cdn15.com/20230321/3484_201869fe/index.m3u8
古代战场2-17,https://vip15.play-cdn15.com/20230321/3483_24140c31/index.m3u8
古代战场2-18,https://vip15.play-cdn15.com/20230321/3482_92b55254/index.m3u8
古代战场2-19,https://yzzy.play-cdn14.com/20230322/16149_47118624/index.m3u8
古代战场2-20,https://yzzy.play-cdn14.com/20230322/16148_f6a96d1e/index.m3u8
古代战场2-21,https://yzzy.play-cdn14.com/20230322/16147_de4d3007/index.m3u8

【大唐狄公案】,
大唐狄公案-01,https://yzzy1.play-cdn20.com/20240206/16417_45008fa3/index.m3u8
大唐狄公案-02,https://yzzy1.play-cdn20.com/20240206/16416_3fa2fe1d/index.m3u8
大唐狄公案-03,https://yzzy.play-cdn19.com/20240206/19158_d170bf64/index.m3u8
大唐狄公案-04,https://yzzy.play-cdn19.com/20240206/19157_e12ed26e/index.m3u8
大唐狄公案-05,https://yzzy.play-cdn19.com/20240207/19211_4e6e0e46/index.m3u8
大唐狄公案-06,https://yzzy.play-cdn19.com/20240207/19212_e7b8967c/index.m3u8
大唐狄公案-07,https://yzzy1.play-cdn20.com/20240208/16560_c6a80eeb/index.m3u8
大唐狄公案-08,https://yzzy1.play-cdn20.com/20240208/16559_4351dbc0/index.m3u8
大唐狄公案-09,https://yzzy1.play-cdn20.com/20240211/16740_1b5079b2/index.m3u8
大唐狄公案-10,https://yzzy1.play-cdn20.com/20240211/16741_63a94ae9/index.m3u8
大唐狄公案-11,https://yzzy1.play-cdn20.com/20240212/16779_9fa8d1bf/index.m3u8
大唐狄公案-12,https://yzzy1.play-cdn20.com/20240212/16778_83a7282d/index.m3u8
大唐狄公案-13,https://yzzy.play-cdn19.com/20240213/19801_a7910a83/index.m3u8
大唐狄公案-14,https://yzzy.play-cdn19.com/20240213/19800_76330a09/index.m3u8
大唐狄公案-15,https://yzzy1.play-cdn1.com/20240214/16482_b0a8a951/index.m3u8
大唐狄公案-16,https://yzzy1.play-cdn1.com/20240214/16481_3641f9c8/index.m3u8
大唐狄公案-17,https://yzzy.play-cdn19.com/20240215/19915_36f5bddc/index.m3u8
大唐狄公案-18,https://yzzy.play-cdn19.com/20240215/19914_78e28151/index.m3u8

【南来北往】,
南来北往-01,https://yzzy1.play-cdn1.com/20240206/15460_6aabb762/index.m3u8
南来北往-02,https://yzzy1.play-cdn1.com/20240206/15459_bd9bca4a/index.m3u8
南来北往-03,https://yzzy1.play-cdn20.com/20240206/16411_808fa9ea/index.m3u8
南来北往-04,https://yzzy1.play-cdn20.com/20240206/16410_49f6ec0e/index.m3u8
南来北往-05,https://yzzy1.play-cdn20.com/20240207/16512_5e3a710a/index.m3u8
南来北往-06,https://yzzy1.play-cdn20.com/20240207/16511_ad6f027f/index.m3u8
南来北往-07,https://yzzy.play-cdn19.com/20240208/19296_29e5e2d7/index.m3u8
南来北往-08,https://yzzy.play-cdn19.com/20240208/19295_9909272b/index.m3u8
南来北往-09,https://yzzy1.play-cdn20.com/20240209/16632_26f9dce1/index.m3u8
南来北往-10,https://yzzy.play-cdn19.com/20240210/19391_14074884/index.m3u8
南来北往-11,https://yzzy.play-cdn19.com/20240210/19390_fe090fd9/index.m3u8
南来北往-12,https://yzzy1.play-cdn20.com/20240211/16744_3401f7a0/index.m3u8
南来北往-13,https://yzzy1.play-cdn20.com/20240211/16743_657656da/index.m3u8
南来北往-14,https://yzzy1.play-cdn1.com/20240212/16138_dd8a9411/index.m3u8
南来北往-15,https://yzzy1.play-cdn1.com/20240212/16137_5e9a2c7b/index.m3u8
南来北往-16,https://yzzy.play-cdn19.com/20240213/19806_cd3ef3ce/index.m3u8
南来北往-17,https://yzzy.play-cdn19.com/20240213/19805_a03fa4a8/index.m3u8
南来北往-18,https://yzzy1.play-cdn1.com/20240214/16499_2fdcfb6a/index.m3u8

【三体】,
三体-01,https://yzzy.play-cdn14.com/20230115/1997_3992be88/index.m3u8
三体-02,https://yzzy.play-cdn14.com/20230115/1996_fa060c1a/index.m3u8
三体-03,https://yzzy.play-cdn14.com/20230115/1995_f5fdf35d/index.m3u8
三体-04,https://yzzy.play-cdn14.com/20230115/1994_5f23d121/index.m3u8
三体-05,https://yzzy.play-cdn12.com/20230116/14820_4381b7cc/index.m3u8
三体-06,https://yzzy.play-cdn12.com/20230118/14902_53fe1162/index.m3u8
三体-07,https://yzzy.play-cdn12.com/20230119/14960_ca275e9c/index.m3u8
三体-08,https://yzzy.play-cdn12.com/20230119/14987_e4db6a7d/index.m3u8
三体-09,https://yzzy.play-cdn10.com/20230120/23566_8b9c377b/index.m3u8
三体-10,https://yzzy.play-cdn12.com/20230122/15155_6f6792d5/index.m3u8
三体-11,https://yzzy.play-cdn10.com/20230123/23804_244abc70/index.m3u8
三体-12,https://yzzy.play-cdn12.com/20230124/15247_5d64fbdb/index.m3u8
三体-13,https://yzzy.play-cdn10.com/20230125/24022_2ee9dc05/index.m3u8
三体-14,https://yzzy.play-cdn13.com/20230126/8827_6a16b62f/index.m3u8
三体-15,https://yzzy.play-cdn14.com/20230127/5588_a13c086e/index.m3u8
三体-16,https://yzzy.play-cdn14.com/20230129/5875_65aa8598/index.m3u8
三体-17,https://yzzy.play-cdn14.com/20230130/6030_99c53ea1/index.m3u8
三体-18,https://yzzy.play-cdn14.com/20230131/6136_aa2c6f89/index.m3u8
三体-19,https://yzzy.play-cdn12.com/20230201/17396_981dc194/index.m3u8
三体-20,https://yzzy.play-cdn12.com/20230202/17488_3d92d838/index.m3u8
三体-21,https://yzzy.play-cdn14.com/20230203/6789_705a9411/index.m3u8
三体-22,https://yzzy.play-cdn14.com/20230203/6794_bb1163a2/index.m3u8
三体-23,https://yzzy.play-cdn14.com/20230203/6793_a33ce9ac/index.m3u8
三体-24,https://yzzy.play-cdn14.com/20230203/6792_40ef0c4c/index.m3u8
三体-25,https://yzzy.play-cdn14.com/20230203/6791_6f9446b1/index.m3u8
三体-26,https://yzzy.play-cdn14.com/20230203/6790_04431d13/index.m3u8
三体-27,https://yzzy.play-cdn12.com/20230203/17678_02bc9ddd/index.m3u8
三体-28,https://yzzy.play-cdn12.com/20230203/17677_3744fa07/index.m3u8
三体-29,https://yzzy.play-cdn12.com/20230203/17676_44c8a923/index.m3u8
三体-30,https://yzzy.play-cdn12.com/20230203/17675_7a5744ee/index.m3u8

【异人之下】,
异人之下-01,https://yzzy1.play-cdn16.com/20230804/15319_5a21bca6/index.m3u8
异人之下-02,https://yzzy1.play-cdn16.com/20230804/15322_e4ca85dd/index.m3u8
异人之下-03,https://yzzy1.play-cdn16.com/20230804/15321_5e9635f7/index.m3u8
异人之下-04,https://yzzy1.play-cdn16.com/20230804/15320_9618baf9/index.m3u8
异人之下-05,https://yzzy.play-cdn19.com/20230906/3065_6e9c809c/index.m3u8
异人之下-06,https://yzzy.play-cdn19.com/20230906/3064_52f3f491/index.m3u8
异人之下-07,https://yzzy.play-cdn19.com/20230907/3147_27aafd26/index.m3u8
异人之下-08,https://yzzy.play-cdn19.com/20230907/3146_a641aae9/index.m3u8
异人之下-09,https://yzzy.play-cdn19.com/20230908/3290_bb1b23c0/index.m3u8
异人之下-10,https://yzzy1.play-cdn16.com/20230909/19759_b6b6501c/index.m3u8
异人之下-11,https://yzzy1.play-cdn16.com/20230909/19758_e23c77d9/index.m3u8
异人之下-12,https://yzzy.play-cdn17.com/20230910/18373_d1407d2a/index.m3u8
异人之下-13,https://yzzy.play-cdn19.com/20230911/3872_5229a6d4/index.m3u8
异人之下-14,https://yzzy.play-cdn19.com/20230912/4049_11dcb93a/index.m3u8
异人之下-15,https://yzzy.play-cdn19.com/20230912/4048_c0575656/index.m3u8
异人之下-16,https://yzzy.play-cdn17.com/20230913/18525_f1efa020/index.m3u8
异人之下-17,https://yzzy.play-cdn17.com/20230914/18618_7a0c132a/index.m3u8
异人之下-18,https://yzzy.play-cdn19.com/20230915/4445_bd10d7de/index.m3u8
异人之下-19,https://yzzy.play-cdn17.com/20230916/18729_595cedc2/index.m3u8
异人之下-20,https://yzzy.play-cdn19.com/20230917/4825_d1224e38/index.m3u8
异人之下-21,https://yzzy1.play-cdn16.com/20230919/20908_0a584b33/index.m3u8
异人之下-22,https://yzzy1.play-cdn16.com/20230920/20960_d324d9ba/index.m3u8
异人之下-23,https://yzzy1.play-cdn1.com/20230921/145_b1dd5c6b/index.m3u8
异人之下-24,https://yzzy1.play-cdn1.com/20230922/319_66b85a1a/index.m3u8
异人之下-25,https://yzzy1.play-cdn1.com/20230922/318_1f8367c9/index.m3u8
异人之下-26,https://yzzy.play-cdn19.com/20230922/5150_79b5fa8a/index.m3u8
异人之下-27,https://yzzy.play-cdn19.com/20230922/5149_c1d2e13e/index.m3u8

【米小圈上学记】,
米小圈上学记-01,https://yzzy.play-cdn11.com/20221231/21081_bfe28e32/index.m3u8
米小圈上学记-02,https://yzzy.play-cdn11.com/20221231/21080_52c9cadd/index.m3u8
米小圈上学记-03,https://yzzy.play-cdn11.com/20221231/21079_a04dbbf7/index.m3u8
米小圈上学记-04,https://yzzy.play-cdn11.com/20221231/21078_bf2d1c35/index.m3u8
米小圈上学记-05,https://yzzy.play-cdn11.com/20230101/21187_e54e99d9/index.m3u8
米小圈上学记-06,https://yzzy.play-cdn11.com/20230101/21186_cf4cf1f9/index.m3u8
米小圈上学记-07,https://yzzy.play-cdn14.com/20230107/710_fe13144f/index.m3u8
米小圈上学记-08,https://yzzy.play-cdn14.com/20230107/709_98e2fde2/index.m3u8
米小圈上学记-09,https://yzzy.play-cdn14.com/20230108/847_fd89691a/index.m3u8
米小圈上学记-10,https://yzzy.play-cdn14.com/20230108/846_20da4e34/index.m3u8
米小圈上学记-11,https://yzzy.play-cdn14.com/20230113/1512_a77fb345/index.m3u8
米小圈上学记-12,https://yzzy.play-cdn14.com/20230113/1511_71da058f/index.m3u8
米小圈上学记-13,https://yzzy.play-cdn14.com/20230114/1785_1116c4a3/index.m3u8
米小圈上学记-14,https://yzzy.play-cdn14.com/20230114/1784_28b46ed3/index.m3u8
米小圈上学记-15,https://yzzy.play-cdn14.com/20230115/1972_04aa43a3/index.m3u8
米小圈上学记-16,https://yzzy.play-cdn14.com/20230115/1971_812eed62/index.m3u8
米小圈上学记-17,https://yzzy.play-cdn12.com/20230120/15035_73e0af8a/index.m3u8
米小圈上学记-18,https://yzzy.play-cdn12.com/20230120/15034_80d31f84/index.m3u8
米小圈上学记-19,https://yzzy.play-cdn10.com/20230121/23678_7c75d3a5/index.m3u8
米小圈上学记-20,https://yzzy.play-cdn10.com/20230121/23677_49844712/index.m3u8
米小圈上学记-21,https://yzzy.play-cdn10.com/20230122/23765_71d134ea/index.m3u8
米小圈上学记-22,https://yzzy.play-cdn10.com/20230122/23764_2f395e64/index.m3u8
米小圈上学记-23,https://yzzy.play-cdn13.com/20230127/8898_71d4fcc4/index.m3u8
米小圈上学记-24,https://yzzy.play-cdn13.com/20230127/8897_3a10c0d7/index.m3u8
米小圈上学记-25,https://yzzy.play-cdn14.com/20230128/5723_d1cb68b7/index.m3u8
米小圈上学记-26,https://yzzy.play-cdn14.com/20230128/5722_c88eb9f0/index.m3u8
米小圈上学记2-01,https://yzzy1.play-cdn1.com/20240212/16145_75a9ed90/index.m3u8
米小圈上学记2-02,https://yzzy1.play-cdn1.com/20240212/16146_c45c2b15/index.m3u8
米小圈上学记2-03,https://yzzy1.play-cdn1.com/20240212/16147_8bd043d7/index.m3u8
米小圈上学记2-04,https://yzzy1.play-cdn1.com/20240212/16148_a0268574/index.m3u8
米小圈上学记2-05,https://yzzy1.play-cdn16.com/20240213/27916_ebe2437b/index.m3u8
米小圈上学记2-06,https://yzzy1.play-cdn20.com/20240214/16938_3c5e7042/index.m3u8

【繁城之下】,
繁城之下-01,https://yzzy.play-cdn19.com/20231013/5827_55e03995/index.m3u8
繁城之下-02,https://yzzy.play-cdn19.com/20231013/5826_f057eddf/index.m3u8
繁城之下-03,https://yzzy1.play-cdn1.com/20231013/2235_4225ea06/index.m3u8
繁城之下-04,https://yzzy1.play-cdn20.com/20231014/1173_db0cb5b0/index.m3u8
繁城之下-05,https://yzzy1.play-cdn20.com/20231015/1232_559b00d2/index.m3u8
繁城之下-06,https://yzzy1.play-cdn20.com/20231016/1324_018b0b50/index.m3u8
繁城之下-07,https://yzzy1.play-cdn20.com/20231017/1453_6a8064b2/index.m3u8
繁城之下-08,https://yzzy1.play-cdn20.com/20231018/1541_2b80cc75/index.m3u8
繁城之下-09,https://yzzy1.play-cdn20.com/20231019/1688_21538cdf/index.m3u8
繁城之下-10,https://yzzy1.play-cdn20.com/20231020/1824_ec5b5a34/index.m3u8
繁城之下-11,https://yzzy1.play-cdn20.com/20231021/1960_8e90cb3c/index.m3u8
繁城之下-12,https://yzzy.play-cdn19.com/20231022/6099_454d44ed/index.m3u8

【莲花楼】,
莲花楼-01,https://yzzy.play-cdn18.com/20230723/1454_107ed5b5/index.m3u8
莲花楼-02,https://yzzy.play-cdn18.com/20230723/1453_5033c7fd/index.m3u8
莲花楼-03,https://yzzy.play-cdn18.com/20230723/1452_b03560cb/index.m3u8
莲花楼-04,https://yzzy1.play-cdn16.com/20230723/13737_8f035d6e/index.m3u8
莲花楼-05,https://yzzy1.play-cdn16.com/20230723/13736_202ed904/index.m3u8
莲花楼-06,https://yzzy1.play-cdn16.com/20230723/13735_a45bfbd3/index.m3u8
莲花楼-07,https://yzzy.play-cdn18.com/20230724/1540_4d4292f4/index.m3u8
莲花楼-08,https://yzzy.play-cdn18.com/20230724/1539_a018b34e/index.m3u8
莲花楼-09,https://vip15.play-cdn15.com/20230725/21013_90d852ba/index.m3u8
莲花楼-10,https://vip15.play-cdn15.com/20230725/21012_57617ac5/index.m3u8
莲花楼-11,https://yzzy.play-cdn18.com/20230726/1907_90823095/index.m3u8
莲花楼-12,https://yzzy.play-cdn18.com/20230726/1906_97904553/index.m3u8
莲花楼-13,https://yzzy.play-cdn18.com/20230727/2032_a731e3be/index.m3u8
莲花楼-14,https://yzzy.play-cdn18.com/20230727/2031_a8dad928/index.m3u8
莲花楼-15,https://yzzy.play-cdn18.com/20230728/2192_dd34c600/index.m3u8
莲花楼-16,https://yzzy.play-cdn18.com/20230728/2191_e6379edc/index.m3u8
莲花楼-17,https://yzzy.play-cdn18.com/20230729/2571_19bdbb87/index.m3u8
莲花楼-18,https://yzzy.play-cdn18.com/20230729/2570_ef4e639c/index.m3u8
莲花楼-19,https://yzzy.play-cdn18.com/20230802/3106_7a4a645e/index.m3u8
莲花楼-20,https://yzzy.play-cdn18.com/20230802/3105_b682d050/index.m3u8
莲花楼-21,https://vip15.play-cdn15.com/20230803/23015_4e86e509/index.m3u8
莲花楼-22,https://vip15.play-cdn15.com/20230803/23014_fe9c375d/index.m3u8
莲花楼-23,https://vip15.play-cdn15.com/20230804/23078_20ac1f2d/index.m3u8
莲花楼-24,https://vip15.play-cdn15.com/20230804/23077_9e61e4ee/index.m3u8
莲花楼-25,https://yzzy1.play-cdn16.com/20230805/15451_bc6e9933/index.m3u8
莲花楼-26,https://yzzy1.play-cdn16.com/20230805/15450_0ec374bd/index.m3u8
莲花楼-27,https://yzzy1.play-cdn16.com/20230806/15594_28d585a7/index.m3u8
莲花楼-28,https://yzzy1.play-cdn16.com/20230806/15593_03715c19/index.m3u8
莲花楼-29,https://yzzy1.play-cdn16.com/20230807/15699_9506899c/index.m3u8
莲花楼-30,https://yzzy1.play-cdn16.com/20230807/15698_7cd73749/index.m3u8
莲花楼-31,https://vip15.play-cdn15.com/20230808/23304_4b6eb5ea/index.m3u8
莲花楼-32,https://vip15.play-cdn15.com/20230808/23303_b6bf3176/index.m3u8
莲花楼-33,https://yzzy.play-cdn18.com/20230809/4116_72565f4b/index.m3u8
莲花楼-34,https://yzzy.play-cdn18.com/20230809/4117_5d2fa2cf/index.m3u8
莲花楼-35,https://yzzy1.play-cdn16.com/20230809/15862_7b431653/index.m3u8
莲花楼-36,https://yzzy1.play-cdn16.com/20230809/15861_d94bda2b/index.m3u8
莲花楼-37,https://yzzy1.play-cdn16.com/20230809/15863_9ed71f62/index.m3u8
莲花楼-38,https://yzzy.play-cdn18.com/20230809/4120_a5b6b924/index.m3u8
莲花楼-39,https://yzzy.play-cdn18.com/20230809/4119_63e13008/index.m3u8
莲花楼-40,https://yzzy.play-cdn18.com/20230809/4118_d3dca3f2/index.m3u8

【长相思】,
长相思-01,https://yzzy.play-cdn18.com/20230724/1534_1535ef4c/index.m3u8
长相思-02,https://yzzy.play-cdn18.com/20230724/1533_4b9f8599/index.m3u8
长相思-03,https://yzzy.play-cdn18.com/20230724/1532_84c587a9/index.m3u8
长相思-04,https://yzzy1.play-cdn16.com/20230724/13785_da19a3ac/index.m3u8
长相思-05,https://yzzy.play-cdn18.com/20230725/1675_d16c3fd9/index.m3u8
长相思-06,https://yzzy.play-cdn18.com/20230725/1674_85f811fa/index.m3u8
长相思-07,https://yzzy1.play-cdn16.com/20230726/14139_2833ee73/index.m3u8
长相思-08,https://yzzy1.play-cdn16.com/20230726/14138_dda88089/index.m3u8
长相思-09,https://yzzy.play-cdn18.com/20230727/2026_2cebfe4d/index.m3u8
长相思-10,https://yzzy.play-cdn18.com/20230727/2025_a9904347/index.m3u8
长相思-11,https://yzzy1.play-cdn16.com/20230728/14237_c699ccd8/index.m3u8
长相思-12,https://yzzy1.play-cdn16.com/20230728/14236_b822fd96/index.m3u8
长相思-13,https://yzzy1.play-cdn16.com/20230729/14320_337f0d24/index.m3u8
长相思-14,https://yzzy1.play-cdn16.com/20230730/14407_bc8b1717/index.m3u8
长相思-15,https://vip15.play-cdn15.com/20230731/22244_227ef030/index.m3u8
长相思-16,https://vip15.play-cdn15.com/20230731/22243_0bb50e2b/index.m3u8
长相思-17,https://yzzy1.play-cdn16.com/20230801/14701_cf0d9d5b/index.m3u8
长相思-18,https://yzzy1.play-cdn16.com/20230801/14700_450b78e5/index.m3u8
长相思-19,https://yzzy.play-cdn18.com/20230802/3102_7536f914/index.m3u8
长相思-20,https://yzzy.play-cdn18.com/20230802/3101_d7e6d4f6/index.m3u8
长相思-21,https://yzzy1.play-cdn16.com/20230803/15281_b2c902d2/index.m3u8
长相思-22,https://vip15.play-cdn15.com/20230804/23068_d61623fd/index.m3u8
长相思-23,https://vip15.play-cdn15.com/20230807/23243_1684eb90/index.m3u8
长相思-24,https://vip15.play-cdn15.com/20230807/23242_e35f4e26/index.m3u8
长相思-25,https://vip15.play-cdn15.com/20230808/23296_10127dbf/index.m3u8
长相思-26,https://vip15.play-cdn15.com/20230808/23299_7692a66a/index.m3u8
长相思-27,https://vip15.play-cdn15.com/20230809/23419_71fc6bf1/index.m3u8
长相思-28,https://vip15.play-cdn15.com/20230809/23418_766e633a/index.m3u8
长相思-29,https://yzzy1.play-cdn16.com/20230810/16021_c1c6dec9/index.m3u8
长相思-30,https://yzzy1.play-cdn16.com/20230810/16022_7ddbf3e1/index.m3u8
长相思-31,https://yzzy1.play-cdn16.com/20230814/16386_4d0c5208/index.m3u8
长相思-32,https://yzzy1.play-cdn16.com/20230814/16385_56ee2b09/index.m3u8
长相思-33,https://vip15.play-cdn15.com/20230814/23628_de4002b3/index.m3u8
长相思-34,https://yzzy1.play-cdn16.com/20230814/16392_3a8e4c84/index.m3u8
长相思-35,https://yzzy1.play-cdn16.com/20230814/16390_62c78843/index.m3u8
长相思-36,https://vip15.play-cdn15.com/20230814/23633_6a12a79b/index.m3u8
长相思-37,https://yzzy1.play-cdn16.com/20230814/16394_7afe0d87/index.m3u8
长相思-38,https://yzzy1.play-cdn16.com/20230814/16395_d366e143/index.m3u8
长相思-39,https://yzzy1.play-cdn16.com/20230814/16396_f01d4cfa/index.m3u8

【欢喜密探】,
欢喜密探-01,https://yzzy.play-cdn9.com/20221008/3643_82f4fe68/index.m3u8
欢喜密探-02,https://yzzy.play-cdn9.com/20221008/3646_d7332126/index.m3u8
欢喜密探-03,https://yzzy.play-cdn9.com/20221008/3649_e0a4d62c/index.m3u8
欢喜密探-04,https://yzzy.play-cdn9.com/20221008/3647_87a58b91/index.m3u8
欢喜密探-05,https://yzzy.play-cdn9.com/20221008/3648_236e78b1/index.m3u8
欢喜密探-06,https://yzzy.play-cdn9.com/20221008/3650_458946fa/index.m3u8
欢喜密探-07,https://yzzy.play-cdn9.com/20221008/3652_d0119826/index.m3u8
欢喜密探-08,https://yzzy.play-cdn9.com/20221008/3651_dc566796/index.m3u8
欢喜密探-09,https://yzzy.play-cdn9.com/20221008/3660_7970cfde/index.m3u8
欢喜密探-10,https://yzzy.play-cdn9.com/20221008/3661_037a1fbd/index.m3u8
欢喜密探-11,https://yzzy.play-cdn9.com/20221008/3662_def9511b/index.m3u8
欢喜密探-12,https://yzzy.play-cdn9.com/20221008/3663_5f8c2414/index.m3u8
欢喜密探-13,https://yzzy.play-cdn9.com/20221008/3664_f931a89c/index.m3u8
欢喜密探-14,https://yzzy.play-cdn9.com/20221008/3667_2d32630a/index.m3u8
欢喜密探-15,https://yzzy.play-cdn9.com/20221008/3665_5a30e854/index.m3u8
欢喜密探-16,https://yzzy.play-cdn9.com/20221008/3668_2517645f/index.m3u8
欢喜密探-17,https://yzzy.play-cdn9.com/20221008/3666_55a44054/index.m3u8
欢喜密探-18,https://yzzy.play-cdn9.com/20221008/3669_9d271ef6/index.m3u8
欢喜密探-19,https://yzzy.play-cdn9.com/20221008/3685_3767d011/index.m3u8
欢喜密探-20,https://yzzy.play-cdn9.com/20221008/3683_3bcd49d3/index.m3u8
欢喜密探-21,https://yzzy.play-cdn9.com/20221008/3684_f6c359dc/index.m3u8
欢喜密探-22,https://yzzy.play-cdn9.com/20221008/3687_bebeea15/index.m3u8
欢喜密探-23,https://yzzy.play-cdn9.com/20221008/3686_6fdb3692/index.m3u8
欢喜密探-24,https://yzzy.play-cdn9.com/20221008/3688_b1cbc054/index.m3u8
欢喜密探-25,https://yzzy.play-cdn9.com/20221008/3690_f2ee20d6/index.m3u8
欢喜密探-26,https://yzzy.play-cdn9.com/20221008/3689_3d99c897/index.m3u8
欢喜密探-27,https://yzzy.play-cdn9.com/20221008/3691_b47d711f/index.m3u8
欢喜密探-28,https://yzzy.play-cdn9.com/20221008/3702_30cd46a9/index.m3u8
欢喜密探-29,https://yzzy.play-cdn9.com/20221008/3692_78d2e8dd/index.m3u8
欢喜密探-30,https://yzzy.play-cdn9.com/20221008/3703_aedcb8cf/index.m3u8
欢喜密探-31,https://yzzy.play-cdn9.com/20221008/3701_f8022bbe/index.m3u8
欢喜密探-32,https://yzzy.play-cdn9.com/20221008/3705_b5054e17/index.m3u8
欢喜密探-33,https://yzzy.play-cdn9.com/20221008/3704_792b4f18/index.m3u8
欢喜密探-34,https://yzzy.play-cdn9.com/20221008/3700_b47c5843/index.m3u8
欢喜密探-35,https://yzzy.play-cdn9.com/20221008/3706_4ebd9a37/index.m3u8
欢喜密探-36,https://yzzy.play-cdn9.com/20221008/3707_e243cd94/index.m3u8
欢喜密探-37,https://yzzy.play-cdn9.com/20221008/3708_e973218a/index.m3u8
欢喜密探-38,https://yzzy.play-cdn9.com/20221008/3709_41f96448/index.m3u8
欢喜密探-39,https://yzzy.play-cdn9.com/20221008/3710_e25c37f5/index.m3u8
欢喜密探-40,https://yzzy.play-cdn9.com/20221008/3712_e7028fc9/index.m3u8
欢喜密探-41,https://yzzy.play-cdn9.com/20221008/3713_4c7cecd3/index.m3u8
欢喜密探-42,https://yzzy.play-cdn9.com/20221008/3711_9962d58c/index.m3u8
欢喜密探-43,https://yzzy.play-cdn9.com/20221008/3714_ed3a4c0b/index.m3u8
欢喜密探-44,https://yzzy.play-cdn9.com/20221008/3715_8c32ead2/index.m3u8

【阿麦从军】,
阿麦从军-01,https://yzzy1.play-cdn16.com/20240131/27832_6b7abb75/index.m3u8
阿麦从军-02,https://yzzy1.play-cdn16.com/20240131/27833_3d8365cd/index.m3u8
阿麦从军-03,https://yzzy1.play-cdn16.com/20240131/27834_7226d3cb/index.m3u8
阿麦从军-04,https://yzzy1.play-cdn16.com/20240131/27835_c6226ddb/index.m3u8
阿麦从军-05,https://yzzy1.play-cdn16.com/20240131/27836_7df7b78a/index.m3u8
阿麦从军-06,https://yzzy1.play-cdn16.com/20240131/27837_ea2cda5d/index.m3u8
阿麦从军-07,https://yzzy1.play-cdn1.com/20240201/14970_1596a4d0/index.m3u8
阿麦从军-08,https://yzzy1.play-cdn20.com/20240201/14336_1c632015/index.m3u8
阿麦从军-09,https://yzzy1.play-cdn16.com/20240202/27850_66a6c7f0/index.m3u8
阿麦从军-10,https://yzzy1.play-cdn16.com/20240202/27849_195987ef/index.m3u8
阿麦从军-11,https://yzzy1.play-cdn1.com/20240203/15208_241da8b4/index.m3u8
阿麦从军-12,https://yzzy1.play-cdn1.com/20240203/15207_fa5d305e/index.m3u8
阿麦从军-13,.https://yzzy1.play-cdn1.com/20240204/15255_471272a9/index.m3u8
阿麦从军-14,https://yzzy1.play-cdn1.com/20240204/15254_0087df86/index.m3u8
阿麦从军-15,https://yzzy.play-cdn19.com/20240205/19096_8386fdd6/index.m3u8
阿麦从军-16,https://yzzy.play-cdn19.com/20240205/19095_f9f657e5/index.m3u8
阿麦从军-17,https://yzzy1.play-cdn1.com/20240206/15458_e435ab30/index.m3u8
阿麦从军-18,https://yzzy1.play-cdn1.com/20240206/15457_bfd75b80/index.m3u8
阿麦从军-19,https://yzzy1.play-cdn1.com/20240207/15540_93fd86bd/index.m3u8
阿麦从军-20,https://yzzy1.play-cdn1.com/20240207/15539_a7d0fcf8/index.m3u8
阿麦从军-21,https://yzzy1.play-cdn20.com/20240208/16562_51becb27/index.m3u8
阿麦从军-22,https://yzzy1.play-cdn20.com/20240208/16561_d626a421/index.m3u8
阿麦从军-23,https://yzzy1.play-cdn20.com/20240212/16781_d5a00861/index.m3u8
阿麦从军-24,https://yzzy1.play-cdn20.com/20240212/16780_a26b8926/index.m3u8
阿麦从军-25,https://yzzy.play-cdn19.com/20240213/19804_7258c8f7/index.m3u8
阿麦从军-26,https://yzzy.play-cdn19.com/20240213/19803_dea4dacb/index.m3u8
阿麦从军-27,https://yzzy1.play-cdn20.com/20240214/16949_2acba58b/index.m3u8
阿麦从军-28,https://yzzy1.play-cdn20.com/20240214/16948_c1abc8d2/index.m3u8

【长风渡】,
长风渡-01,https://yzzy.play-cdn17.com/20230618/9209_3cc6efcb/index.m3u8
长风渡-02,https://yzzy.play-cdn17.com/20230618/9208_dd5edd22/index.m3u8
长风渡-03,https://yzzy.play-cdn17.com/20230618/9207_f9277ed8/index.m3u8
长风渡-04,https://www.yzzy.play-cdn16.com/20230618/10194_0ec86ae0/index.m3u8
长风渡-05,https://www.yzzy.play-cdn16.com/20230618/10193_97b7b7a8/index.m3u8
长风渡-06,https://www.yzzy.play-cdn16.com/20230618/10192_299b3b4d/index.m3u8
长风渡-07,https://www.yzzy.play-cdn16.com/20230619/10264_9736f1c7/index.m3u8
长风渡-08,https://www.yzzy.play-cdn16.com/20230619/10263_a8cc89b3/index.m3u8
长风渡-09,https://vip15.play-cdn15.com/20230620/16004_991b2969/index.m3u8
长风渡-10,https://vip15.play-cdn15.com/20230620/16003_fad019e4/index.m3u8
长风渡-11,https://yzzy.play-cdn17.com/20230621/9612_580f462f/index.m3u8
长风渡-12,https://yzzy.play-cdn17.com/20230621/9611_4ee9dd5d/index.m3u8
长风渡-13,https://vip15.play-cdn15.com/20230622/16153_6d38c791/index.m3u8
长风渡-14,https://vip15.play-cdn15.com/20230622/16152_672b0008/index.m3u8
长风渡-15,https://vip15.play-cdn15.com/20230623/16266_abba539c/index.m3u8
长风渡-16,https://vip15.play-cdn15.com/20230623/16265_02a87efb/index.m3u8
长风渡-17,https://vip15.play-cdn15.com/20230624/16346_9d37b4d9/index.m3u8
长风渡-18,https://vip15.play-cdn15.com/20230624/16345_a4f1e044/index.m3u8
长风渡-19,https://vip15.play-cdn15.com/20230625/16394_36185612/index.m3u8
长风渡-20,https://vip15.play-cdn15.com/20230625/16393_dc8f4f4c/index.m3u8
长风渡-21,https://vip15.play-cdn15.com/20230629/17499_70d97243/index.m3u8
长风渡-22,https://vip15.play-cdn15.com/20230629/17498_a016bcae/index.m3u8
长风渡-23,https://www.yzzy.play-cdn16.com/20230630/11606_0dfbf8d5/index.m3u8
长风渡-24,https://www.yzzy.play-cdn16.com/20230630/11605_34db916f/index.m3u8
长风渡-25,https://yzzy.play-cdn17.com/20230701/10533_d6c04a74/index.m3u8
长风渡-26,https://yzzy.play-cdn17.com/20230701/10532_ba9d1d3c/index.m3u8
长风渡-27,https://yzzy.play-cdn17.com/20230702/10584_f778f5b2/index.m3u8
长风渡-28,https://yzzy.play-cdn17.com/20230702/10583_dcd96ce9/index.m3u8
长风渡-29,https://yzzy.play-cdn17.com/20230706/10833_ce70d8d9/index.m3u8
长风渡-30,https://www.yzzy.play-cdn16.com/20230706/12659_0e177c77/index.m3u8
长风渡-31,https://yzzy.play-cdn17.com/20230707/10931_1eb88ede/index.m3u8
长风渡-32,https://yzzy.play-cdn17.com/20230707/10930_a9fd20b1/index.m3u8
长风渡-33,https://vip15.play-cdn15.com/20230708/18137_87e4701b/index.m3u8
长风渡-34,https://vip15.play-cdn15.com/20230708/18136_0b33fbf5/index.m3u8
长风渡-35,https://www.yzzy.play-cdn16.com/20230709/12925_f0b54af4/index.m3u8
长风渡-36,https://www.yzzy.play-cdn16.com/20230709/12924_457311ac/index.m3u8
长风渡-37,https://vip15.play-cdn15.com/20230713/19090_f4261900/index.m3u8
长风渡-38,https://yzzy.play-cdn18.com/20230714/524_0d8b9243/index.m3u8
长风渡-39,https://yzzy.play-cdn18.com/20230714/626_55d2f15f/index.m3u8
长风渡-40,https://yzzy.play-cdn18.com/20230714/625_7d41046f/index.m3u8

【大秦帝国之裂变】,
大秦帝国之裂变-01,https://yzzy.play-cdn7.com/20220826/13855_338be9e1/index.m3u8
大秦帝国之裂变-02,https://yzzy.play-cdn7.com/20220826/13856_ff82e3de/index.m3u8
大秦帝国之裂变-03,https://yzzy.play-cdn7.com/20220826/13857_09684586/index.m3u8
大秦帝国之裂变-04,https://yzzy.play-cdn7.com/20220826/13858_0fd421cc/index.m3u8
大秦帝国之裂变-05,https://yzzy.play-cdn7.com/20220826/13859_47f40191/index.m3u8
大秦帝国之裂变-06,https://yzzy.play-cdn7.com/20220826/13860_866a09da/index.m3u8
大秦帝国之裂变-07,https://yzzy.play-cdn7.com/20220826/13861_7e1339b0/index.m3u8
大秦帝国之裂变-08,https://yzzy.play-cdn7.com/20220826/13862_4c2faeba/index.m3u8
大秦帝国之裂变-09,https://yzzy.play-cdn7.com/20220826/13863_51006660/index.m3u8
大秦帝国之裂变-10,https://yzzy.play-cdn7.com/20220826/13864_398c121d/index.m3u8
大秦帝国之裂变-11,https://yzzy.play-cdn7.com/20220826/13865_e7dad584/index.m3u8
大秦帝国之裂变-12,https://yzzy.play-cdn7.com/20220826/13866_11d7295f/index.m3u8
大秦帝国之裂变-13,https://yzzy.play-cdn7.com/20220826/13867_389e11df/index.m3u8
大秦帝国之裂变-14,https://yzzy.play-cdn7.com/20220826/13868_573c29de/index.m3u8
大秦帝国之裂变-15,https://yzzy.play-cdn7.com/20220826/13869_f52dfde1/index.m3u8
大秦帝国之裂变-16,https://yzzy.play-cdn7.com/20220826/13870_7dd670a4/index.m3u8
大秦帝国之裂变-17,https://yzzy.play-cdn7.com/20220826/13871_a7cc2107/index.m3u8
大秦帝国之裂变-18,https://yzzy.play-cdn7.com/20220826/13872_0108ad66/index.m3u8
大秦帝国之裂变-19,https://yzzy.play-cdn7.com/20220826/13873_51a3fb87/index.m3u8
大秦帝国之裂变-20,https://yzzy.play-cdn7.com/20220826/13874_f63fa3ef/index.m3u8
大秦帝国之裂变-21,https://yzzy.play-cdn7.com/20220826/13875_338e4b81/index.m3u8
大秦帝国之裂变-22,https://yzzy.play-cdn7.com/20220826/13876_e0d35333/index.m3u8
大秦帝国之裂变-23,https://yzzy.play-cdn7.com/20220826/13877_7f569bad/index.m3u8
大秦帝国之裂变-24,https://yzzy.play-cdn7.com/20220826/13878_876aeae4/index.m3u8
大秦帝国之裂变-25,https://yzzy.play-cdn7.com/20220826/13879_6fc39c80/index.m3u8
大秦帝国之裂变-26,https://yzzy.play-cdn7.com/20220826/13880_30d3d883/index.m3u8
大秦帝国之裂变-27,https://yzzy.play-cdn7.com/20220826/13881_5883af31/index.m3u8
大秦帝国之裂变-28,https://yzzy.play-cdn7.com/20220826/13882_63d63be7/index.m3u8
大秦帝国之裂变-29,https://yzzy.play-cdn7.com/20220826/13883_a579d78f/index.m3u8
大秦帝国之裂变-30,https://yzzy.play-cdn7.com/20220826/13884_522f3d06/index.m3u8
大秦帝国之裂变-31,https://yzzy.play-cdn7.com/20220826/13885_5c24f767/index.m3u8
大秦帝国之裂变-32,https://yzzy.play-cdn7.com/20220826/13886_1f487f66/index.m3u8
大秦帝国之裂变-33,https://yzzy.play-cdn7.com/20220826/13887_af9febf1/index.m3u8
大秦帝国之裂变-34,https://yzzy.play-cdn7.com/20220826/13888_8c83d477/index.m3u8
大秦帝国之裂变-35,https://yzzy.play-cdn7.com/20220826/13889_53d87df7/index.m3u8
大秦帝国之裂变-36,https://yzzy.play-cdn7.com/20220826/13890_669126f6/index.m3u8
大秦帝国之裂变-37,https://yzzy.play-cdn7.com/20220826/13891_69fb437f/index.m3u8
大秦帝国之裂变-38,https://yzzy.play-cdn7.com/20220826/13892_5c23ab6b/index.m3u8
大秦帝国之裂变-39,https://yzzy.play-cdn7.com/20220826/13893_87a4331d/index.m3u8
大秦帝国之裂变-40,https://yzzy.play-cdn7.com/20220826/13894_f10e89e2/index.m3u8
大秦帝国之裂变-41,https://yzzy.play-cdn7.com/20220826/13895_5e1d0d52/index.m3u8
大秦帝国之裂变-42,https://yzzy.play-cdn7.com/20220826/13896_06edb2ff/index.m3u8
大秦帝国之裂变-43,https://yzzy.play-cdn7.com/20220826/13897_724e6217/index.m3u8
大秦帝国之裂变-44,https://yzzy.play-cdn7.com/20220826/13898_6ce6095d/index.m3u8
大秦帝国之裂变-45,https://yzzy.play-cdn7.com/20220826/13899_c430effc/index.m3u8
大秦帝国之裂变-46,https://yzzy.play-cdn7.com/20220826/13900_fd4aa7ba/index.m3u8
大秦帝国之裂变-47,https://yzzy.play-cdn7.com/20220826/13901_e3e1a51c/index.m3u8
大秦帝国之裂变-48,https://yzzy.play-cdn7.com/20220826/13903_1b55e50a/index.m3u8

【大秦帝国之纵横】,
大秦帝国之纵横-01,https://yzzy.play-cdn8.com/20220706/1470_541274de/index.m3u8
大秦帝国之纵横-02,https://yzzy.play-cdn8.com/20220706/1469_99d67ad0/index.m3u8
大秦帝国之纵横-03,https://yzzy.play-cdn8.com/20220706/1468_f965e7dc/index.m3u8
大秦帝国之纵横-04,https://yzzy.play-cdn8.com/20220706/1467_4e187e5b/index.m3u8
大秦帝国之纵横-05,https://yzzy.play-cdn8.com/20220706/1466_5b3b3a59/index.m3u8
大秦帝国之纵横-06,https://yzzy.play-cdn8.com/20220706/1465_874162a9/index.m3u8
大秦帝国之纵横-07,https://yzzy.play-cdn8.com/20220706/1464_9ef5ef0f/index.m3u8
大秦帝国之纵横-08,https://yzzy.play-cdn8.com/20220706/1463_bd035037/index.m3u8
大秦帝国之纵横-09,https://yzzy.play-cdn8.com/20220706/1462_89bcd23f/index.m3u8
大秦帝国之纵横-10,https://yzzy.play-cdn8.com/20220706/1461_dabe6615/index.m3u8
大秦帝国之纵横-11,https://yzzy.play-cdn8.com/20220706/1460_93b70cca/index.m3u8
大秦帝国之纵横-12,https://yzzy.play-cdn8.com/20220706/1473_495c9c9d/index.m3u8
大秦帝国之纵横-13,https://yzzy.play-cdn8.com/20220706/1459_a09a6650/index.m3u8
大秦帝国之纵横-14,https://yzzy.play-cdn8.com/20220706/1472_2d83c721/index.m3u8
大秦帝国之纵横-15,https://yzzy.play-cdn8.com/20220706/1471_ac3d925b/index.m3u8
大秦帝国之纵横-16,https://yzzy.play-cdn8.com/20220706/1458_a5397403/index.m3u8
大秦帝国之纵横-17,https://yzzy.play-cdn8.com/20220706/1457_3d285dd0/index.m3u8
大秦帝国之纵横-18,https://yzzy.play-cdn8.com/20220706/1456_76490ce6/index.m3u8
大秦帝国之纵横-19,https://yzzy.play-cdn8.com/20220706/1455_a97f2096/index.m3u8
大秦帝国之纵横-20,https://yzzy.play-cdn8.com/20220706/1454_b3c93a9e/index.m3u8
大秦帝国之纵横-21,https://yzzy.play-cdn8.com/20220706/1453_ba43ba84/index.m3u8
大秦帝国之纵横-22,https://yzzy.play-cdn8.com/20220706/1452_69060575/index.m3u8
大秦帝国之纵横-23,https://yzzy.play-cdn8.com/20220706/1451_bfb07810/index.m3u8
大秦帝国之纵横-24,https://yzzy.play-cdn8.com/20220706/1450_50445545/index.m3u8
大秦帝国之纵横-25,https://yzzy.play-cdn8.com/20220706/1449_142b73b5/index.m3u8
大秦帝国之纵横-26,https://yzzy.play-cdn8.com/20220706/1448_6eb2fea9/index.m3u8
大秦帝国之纵横-27,https://yzzy.play-cdn8.com/20220706/1447_43d80138/index.m3u8
大秦帝国之纵横-28,https://yzzy.play-cdn8.com/20220706/1446_dc92395f/index.m3u8
大秦帝国之纵横-29,https://yzzy.play-cdn8.com/20220706/1445_54b7e70e/index.m3u8
大秦帝国之纵横-30,https://yzzy.play-cdn8.com/20220706/1444_ed5b4fc0/index.m3u8
大秦帝国之纵横-31,https://yzzy.play-cdn8.com/20220706/1443_b5775a3d/index.m3u8
大秦帝国之纵横-32,https://yzzy.play-cdn8.com/20220706/1442_1325e5d9/index.m3u8
大秦帝国之纵横-33,https://yzzy.play-cdn8.com/20220706/1441_2278c669/index.m3u8
大秦帝国之纵横-34,https://yzzy.play-cdn8.com/20220706/1440_1030cddc/index.m3u8
大秦帝国之纵横-35,https://yzzy.play-cdn8.com/20220706/1439_949823b9/index.m3u8
大秦帝国之纵横-36,https://yzzy.play-cdn8.com/20220706/1438_4ba6e0c6/index.m3u8
大秦帝国之纵横-37,https://yzzy.play-cdn8.com/20220706/1437_ff4b50a6/index.m3u8
大秦帝国之纵横-38,https://yzzy.play-cdn8.com/20220706/1436_13201bd5/index.m3u8
大秦帝国之纵横-39,https://yzzy.play-cdn8.com/20220706/1435_cfa8e5a8/index.m3u8
大秦帝国之纵横-40,https://yzzy.play-cdn8.com/20220706/1434_59b2ab97/index.m3u8
大秦帝国之纵横-41,https://yzzy.play-cdn8.com/20220706/1433_8d9edea6/index.m3u8
大秦帝国之纵横-42,https://yzzy.play-cdn8.com/20220706/1432_314b0a56/index.m3u8
大秦帝国之纵横-43,https://yzzy.play-cdn8.com/20220706/1431_21e5d0c9/index.m3u8
大秦帝国之纵横-44,https://yzzy.play-cdn8.com/20220706/1430_9070a763/index.m3u8
大秦帝国之纵横-45,https://yzzy.play-cdn8.com/20220706/1429_86e07d94/index.m3u8
大秦帝国之纵横-46,https://yzzy.play-cdn8.com/20220706/1428_79270475/index.m3u8
大秦帝国之纵横-47,https://yzzy.play-cdn8.com/20220706/1427_413df7d8/index.m3u8
大秦帝国之纵横-48,https://yzzy.play-cdn8.com/20220706/1426_2286ab97/index.m3u8
大秦帝国之纵横-49,https://yzzy.play-cdn8.com/20220706/1425_ce8effa5/index.m3u8
大秦帝国之纵横-50,https://yzzy.play-cdn8.com/20220706/1424_1ef21851/index.m3u8
大秦帝国之纵横-51,https://yzzy.play-cdn8.com/20220706/1423_2ffe8ae9/index.m3u8

【大秦帝国之崛起】,
大秦帝国之崛起-01,https://yzzy.play-cdn5.com/20220516/15396_aef8b325/index.m3u8
大秦帝国之崛起-02,https://yzzy.play-cdn5.com/20220516/15395_960415c4/index.m3u8
大秦帝国之崛起-03,https://yzzy.play-cdn5.com/20220516/15400_37860907/index.m3u8
大秦帝国之崛起-04,https://yzzy.play-cdn5.com/20220516/15402_a9b17dc5/index.m3u8
大秦帝国之崛起-05,https://yzzy.play-cdn5.com/20220516/15399_ff5433e7/index.m3u8
大秦帝国之崛起-06,https://yzzy.play-cdn5.com/20220516/15398_095c8b3f/index.m3u8
大秦帝国之崛起-07,https://yzzy.play-cdn5.com/20220516/15403_03a0fc42/index.m3u8
大秦帝国之崛起-08,https://yzzy.play-cdn5.com/20220516/15401_ceefe1f3/index.m3u8
大秦帝国之崛起-09,https://yzzy.play-cdn5.com/20220516/15407_048ddbf7/index.m3u8
大秦帝国之崛起-10,https://yzzy.play-cdn5.com/20220516/15406_995a9a2f/index.m3u8
大秦帝国之崛起-11,https://yzzy.play-cdn5.com/20220516/15408_6d6454a8/index.m3u8
大秦帝国之崛起-12,https://yzzy.play-cdn5.com/20220516/15409_c59f3330/index.m3u8
大秦帝国之崛起-13,https://yzzy.play-cdn5.com/20220516/15410_956188d8/index.m3u8
大秦帝国之崛起-14,https://yzzy.play-cdn5.com/20220516/15412_5f7c4a49/index.m3u8
大秦帝国之崛起-15,https://yzzy.play-cdn5.com/20220516/15411_eba66e09/index.m3u8
大秦帝国之崛起-16,https://yzzy.play-cdn5.com/20220516/15413_d4118aa6/index.m3u8
大秦帝国之崛起-17,https://yzzy.play-cdn5.com/20220516/15416_88b5e36f/index.m3u8
大秦帝国之崛起-18,https://yzzy.play-cdn5.com/20220516/15415_a9cd4c14/index.m3u8
大秦帝国之崛起-19,https://yzzy.play-cdn5.com/20220516/15414_503dd529/index.m3u8
大秦帝国之崛起-20,https://yzzy.play-cdn5.com/20220516/15417_13b72afc/index.m3u8
大秦帝国之崛起-21,https://yzzy.play-cdn5.com/20220516/15420_641a81c9/index.m3u8
大秦帝国之崛起-22,https://yzzy.play-cdn5.com/20220516/15419_245656ae/index.m3u8
大秦帝国之崛起-23,https://yzzy.play-cdn5.com/20220516/15418_9e875442/index.m3u8
大秦帝国之崛起-24,https://yzzy.play-cdn5.com/20220516/15424_e6c87481/index.m3u8
大秦帝国之崛起-25,https://yzzy.play-cdn5.com/20220516/15423_31083d8e/index.m3u8
大秦帝国之崛起-26,https://yzzy.play-cdn5.com/20220516/15422_ca52e208/index.m3u8
大秦帝国之崛起-27,https://yzzy.play-cdn5.com/20220516/15425_66a46b99/index.m3u8
大秦帝国之崛起-28,https://yzzy.play-cdn5.com/20220516/15426_60436f9e/index.m3u8
大秦帝国之崛起-29,https://yzzy.play-cdn5.com/20220516/15427_3f375e20/index.m3u8
大秦帝国之崛起-30,https://yzzy.play-cdn5.com/20220516/15429_dc156054/index.m3u8
大秦帝国之崛起-31,https://yzzy.play-cdn5.com/20220516/15428_732a61c7/index.m3u8
大秦帝国之崛起-32,https://yzzy.play-cdn5.com/20220516/15432_2c1e3f61/index.m3u8
大秦帝国之崛起-33,https://yzzy.play-cdn5.com/20220516/15433_b24002a6/index.m3u8
大秦帝国之崛起-34,https://yzzy.play-cdn5.com/20220516/15434_46ee0504/index.m3u8
大秦帝国之崛起-35,https://yzzy.play-cdn5.com/20220516/15441_6a03a19f/index.m3u8
大秦帝国之崛起-36,https://yzzy.play-cdn5.com/20220516/15435_4a581771/index.m3u8
大秦帝国之崛起-37,https://yzzy.play-cdn5.com/20220516/15437_62f06d68/index.m3u8
大秦帝国之崛起-38,https://yzzy.play-cdn5.com/20220516/15436_0d7f494f/index.m3u8
大秦帝国之崛起-39,https://yzzy.play-cdn5.com/20220516/15439_6934ee18/index.m3u8
大秦帝国之崛起-40,https://yzzy.play-cdn5.com/20220516/15440_334f1f62/index.m3u8

【楚汉传奇】,
楚汉传奇-01,https://yzzy.play-cdn7.com/20220831/15081_8af5706a/index.m3u8
楚汉传奇-02,https://yzzy.play-cdn7.com/20220831/15080_d9a59d19/index.m3u8
楚汉传奇-03,https://yzzy.play-cdn7.com/20220831/15079_2b88e7df/index.m3u8
楚汉传奇-04,https://yzzy.play-cdn7.com/20220831/15078_dc13de85/index.m3u8
楚汉传奇-05,https://yzzy.play-cdn7.com/20220831/15077_005c8f80/index.m3u8
楚汉传奇-06,https://yzzy.play-cdn7.com/20220831/15076_cadf441d/index.m3u8
楚汉传奇-07,https://yzzy.play-cdn7.com/20220831/15075_92ae49f7/index.m3u8
楚汉传奇-08,https://yzzy.play-cdn7.com/20220831/15074_c5aef7bd/index.m3u8
楚汉传奇-09,https://yzzy.play-cdn7.com/20220831/15073_9cdc7cd6/index.m3u8
楚汉传奇-10,https://yzzy.play-cdn7.com/20220831/15072_1b4c8028/index.m3u8
楚汉传奇-11,https://yzzy.play-cdn7.com/20220831/15071_9e691a93/index.m3u8
楚汉传奇-12,https://yzzy.play-cdn7.com/20220831/15070_e391da8d/index.m3u8
楚汉传奇-13,https://yzzy.play-cdn7.com/20220831/15069_6401151e/index.m3u8
楚汉传奇-14,https://yzzy.play-cdn7.com/20220831/15068_1e476939/index.m3u8
楚汉传奇-15,https://yzzy.play-cdn7.com/20220831/15067_b7f91bf0/index.m3u8
楚汉传奇-16,https://yzzy.play-cdn7.com/20220831/15066_03e5dde8/index.m3u8
楚汉传奇-17,https://yzzy.play-cdn7.com/20220831/15065_039a349b/index.m3u8
楚汉传奇-18,https://yzzy.play-cdn7.com/20220831/15064_570b3ec1/index.m3u8
楚汉传奇-19,https://yzzy.play-cdn7.com/20220831/15063_d7c44d82/index.m3u8
楚汉传奇-20,https://yzzy.play-cdn7.com/20220831/15062_9b50b51a/index.m3u8
楚汉传奇-21,https://yzzy.play-cdn7.com/20220831/15061_ced51be6/index.m3u8
楚汉传奇-22,https://yzzy.play-cdn7.com/20220831/15060_9361d36e/index.m3u8
楚汉传奇-23,https://yzzy.play-cdn7.com/20220831/15059_3d2dd4ed/index.m3u8
楚汉传奇-24,https://yzzy.play-cdn7.com/20220831/15058_961c7044/index.m3u8
楚汉传奇-25,https://yzzy.play-cdn7.com/20220831/15057_95609432/index.m3u8
楚汉传奇-26,https://yzzy.play-cdn7.com/20220831/15056_af3d1832/index.m3u8
楚汉传奇-27,https://yzzy.play-cdn7.com/20220831/15055_fe5caaa0/index.m3u8
楚汉传奇-28,https://yzzy.play-cdn7.com/20220831/15054_a5ec4000/index.m3u8
楚汉传奇-29,https://yzzy.play-cdn7.com/20220831/15053_c7916f35/index.m3u8
楚汉传奇-30,https://yzzy.play-cdn7.com/20220831/15052_f4ae4556/index.m3u8
楚汉传奇-31,https://yzzy.play-cdn7.com/20220831/15051_6f892b94/index.m3u8
楚汉传奇-32,https://yzzy.play-cdn7.com/20220831/15050_73ba235e/index.m3u8
楚汉传奇-33,https://yzzy.play-cdn7.com/20220831/15049_25ee3119/index.m3u8
楚汉传奇-34,https://yzzy.play-cdn7.com/20220831/15048_3af90142/index.m3u8
楚汉传奇-35,https://yzzy.play-cdn7.com/20220831/15047_847de192/index.m3u8
楚汉传奇-36,https://yzzy.play-cdn7.com/20220831/15046_481d0dca/index.m3u8
楚汉传奇-37,https://yzzy.play-cdn7.com/20220831/15045_0a8257f4/index.m3u8
楚汉传奇-38,https://yzzy.play-cdn7.com/20220831/15044_8ead2cba/index.m3u8
楚汉传奇-39,https://yzzy.play-cdn7.com/20220831/15043_14c25381/index.m3u8
楚汉传奇-40,https://yzzy.play-cdn7.com/20220831/15042_48a40bd9/index.m3u8
楚汉传奇-41,https://yzzy.play-cdn7.com/20220831/15041_6971383d/index.m3u8
楚汉传奇-42,https://yzzy.play-cdn7.com/20220831/15040_a86c63db/index.m3u8
楚汉传奇-43,https://yzzy.play-cdn7.com/20220831/15039_c9575883/index.m3u8
楚汉传奇-44,https://yzzy.play-cdn7.com/20220831/15038_4460f9c8/index.m3u8
楚汉传奇-45,https://yzzy.play-cdn7.com/20220831/15037_33cda2c3/index.m3u8
楚汉传奇-46,https://yzzy.play-cdn7.com/20220831/15036_7931efd8/index.m3u8
楚汉传奇-47,https://yzzy.play-cdn7.com/20220831/15035_239e8c86/index.m3u8
楚汉传奇-48,https://yzzy.play-cdn7.com/20220831/15032_60c73f9a/index.m3u8
楚汉传奇-49,https://yzzy.play-cdn7.com/20220831/15034_43163ca9/index.m3u8
楚汉传奇-50,https://yzzy.play-cdn7.com/20220831/15033_69873a99/index.m3u8
楚汉传奇-51,https://yzzy.play-cdn7.com/20220831/15031_605d4812/index.m3u8
楚汉传奇-52,https://yzzy.play-cdn7.com/20220831/15030_96989088/index.m3u8
楚汉传奇-53,https://yzzy.play-cdn7.com/20220831/15029_e8975b2d/index.m3u8
楚汉传奇-54,https://yzzy.play-cdn7.com/20220831/15027_504986b8/index.m3u8
楚汉传奇-55,https://yzzy.play-cdn7.com/20220831/15025_33241395/index.m3u8
楚汉传奇-56,https://yzzy.play-cdn7.com/20220831/15024_87b2487c/index.m3u8
楚汉传奇-57,https://yzzy.play-cdn7.com/20220831/15028_78661aed/index.m3u8

"""
# 获取RAW文件内容
url = "https://raw.githubusercontent.com/mlzlzj/iptv/main/iptv_list.txt"
res = requests.get(url)
a="以下央视卫视可切换线路,#genre#\n"+"双击ok键切换,https://cdn2.yzzy-online.com/20220326/2242_a8d593bc/index.m3u8\n" + res.text

# 输出结果到当前目录下的qgdf.txt文件
with open(output_file_path, "w", encoding="utf-8") as output_file:
    output_file.write(intro_content + '\n')
    output_file.write(a + '\n')
    for line in result:
        output_file.write(line + '\n')

print(f"处理的数据合格，已写入 {output_file_path} 文件。", flush=True)
