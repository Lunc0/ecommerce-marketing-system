from sentence_transformers import SentenceTransformer
import sys
import json
import logging

# Configure logging to stderr so it doesn't interfere with stdout JSON
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # 使用 BGE-M3 模型，支持多语言且性能更强
        # BGE-M3 在多语言检索任务上表现极佳，尤其是中英文混合场景
        model_name = 'BAAI/bge-m3'
        
        # 优化: 这里每次调用脚本都会重新加载模型，这在生产环境中效率极低
        # 建议方案: 应该将此脚本作为一个常驻服务运行 (例如通过 Flask/FastAPI)，或者使用 Java 本地的 ONNX Runtime
        # 但鉴于目前架构是 Java 调用 Python 脚本，我们先保持现状，但需注意加载耗时
        model = SentenceTransformer(model_name)
        
        # Read input JSON from stdin
        input_data = sys.stdin.read()
        if not input_data:
            return

        texts = json.loads(input_data)
        
        # BGE-M3 建议:
        # 对于检索任务，查询(Query)应该加前缀，但文档(Passage)不需要
        # 由于我们无法区分本次调用是 Query 还是 Document (脚本通用)，我们假设调用方会处理前缀
        # 或者我们可以约定: 只有当输入是单条且很短时，才可能是 Query
        
        # Generate embeddings
        # normalize_embeddings=True 对余弦相似度计算很重要
        embeddings = model.encode(texts, normalize_embeddings=True).tolist()
        
        # Output JSON to stdout
        print(json.dumps(embeddings))
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
