from sentence_transformers import CrossEncoder
import sys
import json
import logging

# 配置日志
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用轻量级 Cross-Encoder 模型
# BAAI/bge-reranker-base 是目前中文重排序效果极佳的模型
MODEL_NAME = 'BAAI/bge-reranker-base'

def main():
    try:
        # 加载 Cross-Encoder 模型
        # 注意：这里每次调用都会加载模型，生产环境建议作为服务运行
        model = CrossEncoder(MODEL_NAME)
        
        # 从标准输入读取 JSON 数据
        # 格式: {"query": "...", "documents": ["doc1", "doc2", ...]}
        input_data = sys.stdin.read()
        if not input_data:
            return

        data = json.loads(input_data)
        query = data.get('query', '')
        documents = data.get('documents', [])
        
        if not query or not documents:
            print(json.dumps([]))
            return

        # 构造 (Query, Document) 对
        pairs = [[query, doc] for doc in documents]
        
        # 计算相关性分数 (logits)
        scores = model.predict(pairs)
        
        # 将分数转换为列表并输出
        # 输出格式: [score1, score2, ...]，对应输入的 documents 顺序
        print(json.dumps(scores.tolist()))
        
    except Exception as e:
        logger.error(f"Error in reranking: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
