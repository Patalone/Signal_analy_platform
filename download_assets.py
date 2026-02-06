# --- START OF FILE download_assets.py ---
import os
import urllib.request
import ssl

# 忽略 SSL 证书验证 (防止某些环境报错)
ssl._create_default_https_context = ssl._create_unverified_context

# 1. 定义保存路径 (static/lib)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BASE_DIR, "static", "lib")
FONTS_DIR = os.path.join(LIB_DIR, "fonts")

# 2. 定义资源映射 (CDN URL -> 本地文件名)
# 我们将原来的 CDN 链接映射为本地简短的文件名
RESOURCES = [
    # CSS
    {
        "url": "https://cdn.staticfile.org/element-plus/2.4.2/index.css",
        "path": os.path.join(LIB_DIR, "element-plus.css")
    },
    # JS Libraries
    {
        "url": "https://cdn.staticfile.org/vue/3.3.4/vue.global.prod.min.js",
        "path": os.path.join(LIB_DIR, "vue.min.js")
    },
    {
        "url": "https://cdn.staticfile.org/element-plus/2.4.2/index.full.min.js",
        "path": os.path.join(LIB_DIR, "element-plus.min.js")
    },
    {
        "url": "https://cdn.staticfile.org/axios/1.6.0/axios.min.js",
        "path": os.path.join(LIB_DIR, "axios.min.js")
    },
    {
        "url": "https://cdn.staticfile.org/echarts/5.4.3/echarts.min.js",
        "path": os.path.join(LIB_DIR, "echarts.min.js")
    },
    # Element Plus 字体文件 (CSS中会引用，必须下载，否则图标会乱码)
    {
        "url": "https://cdn.staticfile.org/element-plus/2.4.2/fonts/element-icons.woff",
        "path": os.path.join(FONTS_DIR, "element-icons.woff")
    },
    {
        "url": "https://cdn.staticfile.org/element-plus/2.4.2/fonts/element-icons.ttf",
        "path": os.path.join(FONTS_DIR, "element-icons.ttf")
    }
]

def download_file(url, save_path):
    try:
        print(f"正在下载: {os.path.basename(save_path)} ...")
        # 模拟浏览器 User-Agent，防止被拦截
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f" -> 成功")
    except Exception as e:
        print(f" -> 失败: {e}")

if __name__ == "__main__":
    # 创建目录
    if not os.path.exists(LIB_DIR):
        os.makedirs(LIB_DIR)
        print(f"创建目录: {LIB_DIR}")
    
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)
        print(f"创建目录: {FONTS_DIR}")

    print("=== 开始下载前端依赖资源 ===")
    for res in RESOURCES:
        download_file(res["url"], res["path"])
    print("\n=== 下载完成，请修改 index.html ===")