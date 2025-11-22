"""
Flask Web服务器 - 提供图片搜索API
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from image_searcher import ImageSearcher

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局搜索器实例（延迟加载）
searcher = None

def get_searcher():
    """获取搜索器实例（单例模式）"""
    global searcher
    if searcher is None:
        searcher = ImageSearcher(persist_directory="./chroma_db")
    return searcher

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    """搜索API"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_k = int(data.get('top_k', 10))
        
        if not query:
            return jsonify({'error': '查询文字不能为空'}), 400
        
        # 执行搜索
        search_instance = get_searcher()
        results = search_instance.search(query, top_k=top_k)
        
        # 转换图片路径为URL可访问的路径
        for result in results:
            image_path = result['image_path']
            # 确保路径使用正斜杠
            normalized_path = image_path.replace('\\', '/')
            # 如果路径以项目根目录开头，提取相对路径
            cwd_normalized = os.getcwd().replace('\\', '/')
            if normalized_path.startswith(cwd_normalized):
                rel_path = normalized_path[len(cwd_normalized):].lstrip('/')
                result['image_url'] = rel_path
            elif os.path.isabs(normalized_path):
                # 绝对路径，尝试转换为相对路径
                try:
                    rel_path = os.path.relpath(normalized_path, os.getcwd()).replace('\\', '/')
                    result['image_url'] = rel_path
                except:
                    # 如果无法转换，使用文件名
                    result['image_url'] = os.path.basename(normalized_path)
            else:
                result['image_url'] = normalized_path.lstrip('/')
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    """获取数据库统计信息"""
    try:
        search_instance = get_searcher()
        count = search_instance.collection.count()
        return jsonify({
            'success': True,
            'total_images': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供图片文件服务"""
    from flask import send_from_directory
    import urllib.parse
    
    # URL解码
    filename = urllib.parse.unquote(filename)
    
    # 确保文件路径安全
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
    
    # 尝试从不同位置查找图片
    possible_paths = [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), 'images', os.path.basename(filename)),
    ]
    
    # 如果filename包含目录结构，也尝试直接路径
    if '/' in filename:
        possible_paths.insert(0, os.path.join(os.getcwd(), filename))
    
    for path in possible_paths:
        if os.path.isfile(path):
            directory = os.path.dirname(path)
            file_name = os.path.basename(path)
            return send_from_directory(directory, file_name)
    
    return jsonify({'error': 'Image not found'}), 404

@app.route('/<path:filepath>')
def serve_file(filepath):
    """提供文件服务（用于直接路径访问）"""
    from flask import send_from_directory
    import urllib.parse
    
    # URL解码
    filepath = urllib.parse.unquote(filepath)
    
    # 确保文件路径安全
    if '..' in filepath:
        return jsonify({'error': 'Invalid path'}), 400
    
    full_path = os.path.join(os.getcwd(), filepath)
    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)
        return send_from_directory(directory, file_name)
    
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    print("=" * 50)
    print("启动图片搜索Web服务器...")
    print("=" * 50)
    print("访问 http://localhost:5001 使用搜索界面")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001)

