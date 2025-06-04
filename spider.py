import os
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urljoin
import html2text
import tkinter as tk
from tkinter import filedialog, messagebox

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.csdn.net/'
}

def download_image(img_url, save_dir, referer):
    """下载单张图片到本地"""
    try:
        img_headers = headers.copy()
        img_headers['Referer'] = referer
        time.sleep(random.uniform(0.5, 1.5))
        response = requests.get(img_url, headers=img_headers, stream=True)
        if response.status_code == 200:
            # 去掉 URL 中的片段标识符 (# 后的内容)
            img_url = img_url.split('#')[0]
            img_name = os.path.basename(img_url.split('?')[0])
            if not img_name or '.' not in img_name:
                img_name = f"image_{int(time.time())}.jpg"
            img_name = re.sub(r'[\\/:*?"<>|]', '', img_name)
            img_path = os.path.join(save_dir, img_name)
            with open(img_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return img_name
    except Exception as e:
        print(f"下载图片失败: {img_url}, 错误: {e}")
    return None

def process_content_images(content_div, article_url, img_dir):
    """只处理正文内容区域内的图片"""
    if not content_div:
        return None
    content_copy = BeautifulSoup(str(content_div), 'html.parser')
    for img in content_copy.find_all('img'):
        img_url = img.get('src') or img.get('data-src')
        if not img_url:
            continue
        img_url = urljoin(article_url, img_url)
        img_name = download_image(img_url, img_dir, article_url)
        if img_name:
            img['src'] = os.path.join('images', img_name)
        else:
            img['src'] = img_url
    return content_copy

def get_article_content(article_url, output_dir='output'):
    """获取文章内容并精确处理正文图片"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        if 'csdn.net' in article_url:
            platform = 'csdn'
            article_id = re.search(r'/article/details/(\d+)', article_url)
        elif 'cnblogs.com' in article_url:
            platform = 'cnblogs'
            article_id = re.search(r'/p/(\d+)', article_url)
        else:
            print("暂不支持该网站的文章爬取")
            return None, None, None
        article_id = article_id.group(1) if article_id else str(int(time.time()))
        article_dir = os.path.join(output_dir, f"{platform}_{article_id}")
        os.makedirs(article_dir, exist_ok=True)
        img_dir = os.path.join(article_dir, 'images')
        os.makedirs(img_dir, exist_ok=True)
        time.sleep(random.uniform(1, 3))
        response = requests.get(article_url, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print(f"请求失败，状态码: {response.status_code}")
            return None, None, None
        soup = BeautifulSoup(response.text, 'html.parser')
        if platform == 'csdn':
            title = soup.find('h1', class_='title-article')
            title = title.get_text().strip() if title else "无标题"
            content_div = soup.find('article', class_='baidu_pl') or \
                          soup.find('div', id='article_content') or \
                          soup.find('div', class_='blog-content-box')
        elif platform == 'cnblogs':
            title = soup.find('a', id='cb_post_title_url') or soup.find('h1')
            title = title.get_text().strip() if title else "无标题"
            content_div = soup.find('div', id='cnblogs_post_body')
        if not content_div:
            return title, "无法提取文章内容", article_dir
        content_with_images = process_content_images(content_div, article_url, img_dir)
        for element in content_with_images.find_all(['script', 'style', 'iframe', 'svg']):
            element.decompose()
        markdown = html2text.html2text(str(content_with_images))
        markdown = re.sub(r'\n{3,}', '\n\n', markdown.strip())
        return title, markdown, article_dir
    except Exception as e:
        print(f"获取文章内容时出错: {e}")
        return None, None, None

def start_gui():
    """启动GUI界面"""
    def add_url():
        url = url_entry.get().strip()
        if url:
            url_listbox.insert(tk.END, url)
            url_entry.delete(0, tk.END)

    def remove_url():
        selected = url_listbox.curselection()
        if selected:
            url_listbox.delete(selected)

    def select_output_dir():
        path = filedialog.askdirectory()
        if path:
            output_dir_var.set(path)

    def start_crawling():
        output_dir = output_dir_var.get()
        if not output_dir:
            messagebox.showerror("错误", "请选择保存路径")
            return
        urls = url_listbox.get(0, tk.END)
        if not urls:
            messagebox.showerror("错误", "请添加至少一个文章URL")
            return
        for url in urls:
            title, content, article_dir = get_article_content(url, output_dir)
            if title and content and article_dir:
                md_file = os.path.join(article_dir, f"{title}.md")
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {title}\n\n")
                    f.write(f"原文链接: [{url}]({url})\n\n")
                    f.write(content)
                messagebox.showinfo("成功", f"文章已保存到: {md_file}")
            else:
                messagebox.showerror("失败", f"未能获取文章内容: {url}")

    # 创建主窗口
    root = tk.Tk()
    root.title("文章爬取工具")

    # URL输入框
    tk.Label(root, text="文章URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    url_entry = tk.Entry(root, width=50)
    url_entry.grid(row=0, column=1, padx=5, pady=5)
    tk.Button(root, text="添加", command=add_url).grid(row=0, column=2, padx=5, pady=5)

    # URL列表
    url_listbox = tk.Listbox(root, width=70, height=10)
    url_listbox.grid(row=1, column=0, columnspan=2, padx=5, pady=5)
    tk.Button(root, text="移除", command=remove_url).grid(row=1, column=2, padx=5, pady=5)

    # 保存路径选择
    tk.Label(root, text="保存路径:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    output_dir_var = tk.StringVar()
    tk.Entry(root, textvariable=output_dir_var, width=50).grid(row=2, column=1, padx=5, pady=5)
    tk.Button(root, text="选择", command=select_output_dir).grid(row=2, column=2, padx=5, pady=5)

    # 开始爬取按钮
    tk.Button(root, text="开始爬取", command=start_crawling).grid(row=3, column=0, columnspan=3, pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_gui()