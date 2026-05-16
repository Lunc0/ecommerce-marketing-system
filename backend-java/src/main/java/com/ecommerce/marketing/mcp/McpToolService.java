package com.ecommerce.marketing.mcp;

import com.ecommerce.marketing.model.User;
import com.ecommerce.marketing.repository.UserRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.File;
import java.io.IOException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class McpToolService {

    private final UserRepository userRepository;
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;
    private final JdbcTemplate jdbcTemplate;

    // ChromaDB 配置
    private static final String CHROMA_URL = "http://localhost:8000/api/v1";
    private static final String COLLECTION_PRODUCTS = "ecommerce_products";
    private static final String COLLECTION_SCRIPTS = "marketing_scripts";

    private final RestTemplate restTemplate;
    // 缓存集合ID
    private String productCollectionId;
    private String scriptCollectionId;

    private static final Set<String> SUPPORTED_TOOLS = Set.of(
            "get_redis_profile",
            "get_mysql_profile",
            "get_user_context",
            "search_knowledge",
            "search_marketing_scripts",
            "get_product_details",
            "ingest_product_knowledge",
            "ingest_marketing_scripts",
            "sync_mysql_to_vector",
            "send_sms",
            "skip_marketing",
            "check_message_limit",
            "record_message_sent");

    public McpToolService(UserRepository userRepository,
            StringRedisTemplate stringRedisTemplate,
            ObjectMapper objectMapper,
            JdbcTemplate jdbcTemplate,
            RestTemplate restTemplate) {
        this.userRepository = userRepository;
        this.stringRedisTemplate = stringRedisTemplate;
        this.objectMapper = objectMapper;
        this.jdbcTemplate = jdbcTemplate;
        this.restTemplate = restTemplate;
    }

    public List<ToolDescriptor> listTools() {
        return List.of(
                new ToolDescriptor("get_user_context", "获取用户画像上下文", schema(
                        Map.of("user_id", Map.of("type", "string")),
                        List.of("user_id"))),
                new ToolDescriptor("search_knowledge", "搜索商品知识库", schema(
                        Map.of(
                                "query", Map.of("type", "string"),
                                "n_results", Map.of("type", "number")),
                        List.of("query"))),
                new ToolDescriptor("search_marketing_scripts", "搜索营销话术库", schema(
                        Map.of(
                                "query", Map.of("type", "string", "description", "搜索意图或关键词"),
                                "scenario",
                                Map.of("type", "string", "description",
                                        "场景: cart_abandon(挽留), new_user(新人), price_drop(降价)"),
                                "n_results", Map.of("type", "number")),
                        List.of("query"))),
                new ToolDescriptor("get_product_details", "根据 SKU 获取商品详情", schema(
                        Map.of("product_id", Map.of("type", "string")),
                        List.of("product_id"))),
                new ToolDescriptor("ingest_product_knowledge", "批量写入商品知识库", schema(
                        Map.of("products", Map.of("type", "array")),
                        List.of("products"))),
                new ToolDescriptor("ingest_marketing_scripts", "批量写入营销话术", schema(
                        Map.of("scripts", Map.of("type", "array")),
                        List.of("scripts"))),
                new ToolDescriptor("sync_mysql_to_vector", "从 MySQL 同步全量数据到向量库", schema(
                        Map.of(),
                        List.of())),
                new ToolDescriptor("send_sms", "发送营销短信", schema(
                        Map.of(
                                "user_id", Map.of("type", "string"),
                                "phone", Map.of("type", "string"),
                                "message", Map.of("type", "string")),
                        List.of("user_id", "phone", "message"))),
                new ToolDescriptor("skip_marketing", "跳过营销并记录原因", schema(
                        Map.of(
                                "user_id", Map.of("type", "string"),
                                "reason", Map.of("type", "string")),
                        List.of("user_id", "reason"))),
                new ToolDescriptor("check_message_limit", "Check if user has reached message limit (debounce)", schema(
                        Map.of("user_id", Map.of("type", "string")),
                        List.of("user_id"))),
                new ToolDescriptor("record_message_sent", "Record that a message was sent to user (for debounce)",
                        schema(
                                Map.of("user_id", Map.of("type", "string")),
                                List.of("user_id"))));
    }

    public boolean supportsTool(String name) {
        return name != null && SUPPORTED_TOOLS.contains(name);
    }

    public Object callTool(String name, Map<String, Object> arguments) {
        if (arguments == null) {
            arguments = Map.of();
        }
        return switch (name) {
            case "get_redis_profile" -> getRedisProfile(getString(arguments, "user_id"));
            case "get_mysql_profile" -> getMysqlProfile(getString(arguments, "user_id"));
            case "get_user_context" -> getUserContext(getString(arguments, "user_id"));
            case "search_knowledge" -> searchKnowledge(
                    getString(arguments, "query"),
                    getInt(arguments, "n_results", 3));
            case "search_marketing_scripts" -> searchMarketingScripts(
                    getString(arguments, "query"),
                    getString(arguments, "scenario", ""),
                    getInt(arguments, "n_results", 3));
            case "get_product_details" -> getProductDetails(getString(arguments, "product_id"));
            case "ingest_product_knowledge" -> ingestProductKnowledge(getList(arguments, "products"));
            case "ingest_marketing_scripts" -> ingestMarketingScripts(getList(arguments, "scripts"));
            case "sync_mysql_to_vector" -> syncMysqlToVector();
            case "send_sms" -> sendSms(
                    getString(arguments, "user_id"),
                    getString(arguments, "phone"),
                    getString(arguments, "message"));
            case "skip_marketing" -> skipMarketing(
                    getString(arguments, "user_id"),
                    getString(arguments, "reason"));
            case "check_message_limit" -> checkMessageLimit(getString(arguments, "user_id"));
            case "record_message_sent" -> recordMessageSent(getString(arguments, "user_id"));
            default -> Map.of("error", "UNKNOWN_TOOL");
        };
    }

    private Map<String, Object> getUserContext(String userId) {
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("user_id", userId);
        Map<String, Object> redisProfile = getRedisProfile(userId);
        Map<String, Object> mysqlProfile = getMysqlProfile(userId);
        context.put("redis_profile", redisProfile);
        context.put("mysql_profile", mysqlProfile);
        if (redisProfile != null && mysqlProfile != null) {
            Map<String, Object> combined = new LinkedHashMap<>(mysqlProfile);
            combined.put("cached_tags", redisProfile.getOrDefault("identity_tags", List.of()));
            combined.put("cached_spending_tier", redisProfile.get("spending_tier"));
            context.put("combined_context", combined);
        } else {
            context.put("combined_context", null);
        }
        return context;
    }

    private Map<String, Object> getRedisProfile(String userId) {
        String key = "user:profile:" + userId;
        String json = stringRedisTemplate.opsForValue().get(key);
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<>() {
            });
        } catch (Exception e) {
            return null;
        }
    }

    private Map<String, Object> getMysqlProfile(String userId) {
        Long id = parseUserId(userId);
        if (id == null) {
            return null;
        }
        Optional<User> userOptional = userRepository.findById(id);
        if (userOptional.isEmpty()) {
            return null;
        }
        User user = userOptional.get();
        List<String> tags = parseTags(user.getIdentityTags());
        Map<String, Object> detailedInfo = new LinkedHashMap<>();
        detailedInfo.put("id", user.getId());
        detailedInfo.put("name", user.getName());
        detailedInfo.put("spending_tier", user.getSpendingTier() != null ? user.getSpendingTier().name() : null);
        detailedInfo.put("identity_tags", tags);
        detailedInfo.put("created_at", user.getCreatedAt());
        detailedInfo.put("updated_at", user.getUpdatedAt());

        Map<String, Object> profile = new LinkedHashMap<>();
        profile.put("id", user.getId());
        profile.put("name", user.getName());
        profile.put("spending_tier", user.getSpendingTier() != null ? user.getSpendingTier().name() : null);
        profile.put("identity_tags", tags);
        profile.put("detailed_info", detailedInfo);

        try {
            Map<String, Object> activity = jdbcTemplate.queryForMap(
                    """
                            SELECT COUNT(*) as total_clicks, COUNT(DISTINCT sku_id) as unique_products
                            FROM user_behavior
                            WHERE user_id = ?
                              AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                            """,
                    id);
            profile.put("recent_activity", Map.of(
                    "total_clicks_30d", activity.getOrDefault("total_clicks", 0),
                    "unique_products_viewed_30d", activity.getOrDefault("unique_products", 0)));
        } catch (DataAccessException ignored) {
        }

        return profile;
    }

    // 向量搜索辅助方法
    private List<Map<String, Object>> searchKnowledge(String query, int nResults) {
        if (query == null || query.isBlank()) {
            return List.of();
        }

        try {
            // 1. 生成查询向量
            List<Double> queryEmbedding = generateEmbedding(query);
            if (queryEmbedding == null || queryEmbedding.isEmpty()) {
                return List.of();
            }

            // 2. 确保集合存在
            String colId = ensureCollection(COLLECTION_PRODUCTS);
            if (colId == null) {
                return List.of();
            }

            // 3. 执行向量搜索 (Recall / 粗排)
            // 稍微放大召回数量，给 Cross-Encoder 留出筛选空间 (Top-K * 3)
            int recallCount = nResults * 3;
            Map<String, Object> request = new HashMap<>();
            request.put("query_embeddings", List.of(queryEmbedding));
            request.put("n_results", recallCount);

            Map<String, Object> response = restTemplate.postForObject(
                    CHROMA_URL + "/collections/" + colId + "/query",
                    request,
                    Map.class);

            // 4. 解析初步结果
            List<Map<String, Object>> candidates = parseChromaResponse(response);
            if (candidates.isEmpty()) {
                return List.of();
            }

            // 5. 执行 Cross-Encoder 重排序 (Rerank / 精排)
            List<Map<String, Object>> rerankedResults = rerankResults(query, candidates);

            // 6. 返回 Top-K
            return rerankedResults.stream()
                    .limit(nResults)
                    .collect(Collectors.toList());

        } catch (Exception e) {
            System.err.println("搜索知识库失败: " + e.getMessage());
            e.printStackTrace();
            return List.of();
        }
    }

    // Cross-Encoder 重排序
    private List<Map<String, Object>> rerankResults(String query, List<Map<String, Object>> candidates) {
        try {
            // 准备输入数据
            List<String> documents = candidates.stream()
                    .map(c -> (String) c.get("content")) // 确保 parseChromaResponse 返回了 content 字段
                    .collect(Collectors.toList());

            // 如果文档为空，跳过重排
            if (documents.isEmpty() || documents.stream().allMatch(d -> d == null)) {
                return candidates;
            }

            Map<String, Object> inputData = Map.of(
                    "query", query,
                    "documents", documents);

            String jsonInput = objectMapper.writeValueAsString(inputData);

            // 确定脚本路径
            File script = new File("src/main/scripts/rerank.py");
            if (!script.exists()) {
                script = new File("backend-java/src/main/scripts/rerank.py");
            }

            // 调用 Python 脚本
            ProcessBuilder pb = new ProcessBuilder("python", script.getAbsolutePath());
            Process process = pb.start();

            // 写入输入
            try (OutputStream os = process.getOutputStream()) {
                os.write(jsonInput.getBytes(StandardCharsets.UTF_8));
                os.flush();
            }

            // 读取输出
            String jsonOutput = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            int exitCode = process.waitFor();

            if (exitCode != 0) {
                String errorOutput = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
                System.err.println("Rerank script error: " + errorOutput);
                return candidates; // 降级策略: 脚本失败则返回原结果
            }

            // 解析分数
            List<Double> scores = objectMapper.readValue(jsonOutput, new TypeReference<List<Double>>() {
            });

            // 将分数合并回结果并在 Java 端排序
            for (int i = 0; i < candidates.size(); i++) {
                if (i < scores.size()) {
                    candidates.get(i).put("score", scores.get(i));
                }
            }

            // 按分数降序排序，并过滤低分结果 (Threshold > 0)
            return candidates.stream()
                    .filter(c -> c.containsKey("score")) // 确保有分数
                    // .filter(c -> (double) c.get("score") > -10.0) // BGE-Reranker
                    // 分数范围较宽，暂不过滤过狠，保留 Top-K 即可
                    .sorted((a, b) -> Double.compare((double) b.get("score"), (double) a.get("score")))
                    .collect(Collectors.toList());

        } catch (Exception e) {
            System.err.println("重排序失败: " + e.getMessage());
            return candidates; // 降级
        }
    }

    private List<Map<String, Object>> searchMarketingScripts(String query, String scenario, int nResults) {
        if (query == null || query.isBlank()) {
            return List.of();
        }

        try {
            List<Double> queryEmbedding = generateEmbedding(query);
            if (queryEmbedding != null && !queryEmbedding.isEmpty()) {
                String colId = ensureCollection(COLLECTION_SCRIPTS);
                if (colId == null)
                    return List.of();

                Map<String, Object> request = new HashMap<>();
                request.put("query_embeddings", List.of(queryEmbedding));
                request.put("n_results", nResults);

                // 如果指定了场景，增加 Metadata 过滤
                if (scenario != null && !scenario.isBlank()) {
                    request.put("where", Map.of("scenario", scenario));
                }

                Map<String, Object> response = restTemplate.postForObject(
                        CHROMA_URL + "/collections/" + colId + "/query",
                        request,
                        Map.class);

                // 解析脚本结果 (结构与商品略有不同)
                return parseScriptResponse(response);
            }
        } catch (Exception e) {
            System.err.println("话术搜索失败: " + e.getMessage());
        }
        return List.of();
    }

    private Map<String, Object> checkMessageLimit(String userId) {
        if (userId == null || userId.isBlank()) {
            return Map.of("allowed", false, "reason", "missing_user_id");
        }

        String key = "msg_limit:" + userId;
        String lastSent = stringRedisTemplate.opsForValue().get(key);

        if (lastSent != null) {
            return Map.of("allowed", false, "reason", "limit_reached", "ttl_seconds",
                    stringRedisTemplate.getExpire(key));
        }

        return Map.of("allowed", true);
    }

    private Map<String, Object> recordMessageSent(String userId) {
        if (userId == null || userId.isBlank()) {
            return Map.of("status", "error");
        }

        // 设置 30 分钟过期时间
        stringRedisTemplate.opsForValue().set("msg_limit:" + userId, String.valueOf(System.currentTimeMillis()), 30,
                TimeUnit.MINUTES);
        return Map.of("status", "success");
    }

    private List<Map<String, Object>> parseScriptResponse(Map<String, Object> response) {
        List<Map<String, Object>> results = new ArrayList<>();
        if (response == null)
            return results;

        List<List<String>> ids = (List<List<String>>) response.get("ids");
        List<List<Map<String, Object>>> metadatas = (List<List<Map<String, Object>>>) response.get("metadatas");
        List<List<Double>> distances = (List<List<Double>>) response.get("distances");
        List<List<String>> documents = (List<List<String>>) response.get("documents");

        if (ids != null && !ids.isEmpty() && !ids.get(0).isEmpty()) {
            for (int i = 0; i < ids.get(0).size(); i++) {
                Map<String, Object> result = new LinkedHashMap<>();
                Map<String, Object> meta = metadatas.get(0).get(i);

                result.put("id", ids.get(0).get(i));
                result.put("scenario", meta.get("scenario"));
                result.put("tags", meta.get("tags"));

                if (documents != null && !documents.isEmpty() && documents.get(0).size() > i) {
                    result.put("content", documents.get(0).get(i));
                }

                results.add(result);
            }
        }
        return results;
    }

    private List<Double> generateEmbedding(String text) {
        try {
            File script = new File("src/main/scripts/embed.py");
            if (!script.exists()) {
                // 为测试或不同工作目录提供回退路径
                script = new File("backend-java/src/main/scripts/embed.py");
            }

            ProcessBuilder pb = new ProcessBuilder("python", script.getAbsolutePath());
            Process process = pb.start();

            // 将输入写入标准输入
            try (var writer = process.getOutputStream()) {
                objectMapper.writeValue(writer, List.of(text));
            }

            // 从标准输出读取输出
            List<List<Double>> result = objectMapper.readValue(process.getInputStream(), new TypeReference<>() {
            });

            // 等待完成
            if (!process.waitFor(10, TimeUnit.SECONDS)) {
                process.destroy();
                return null;
            }

            return result.isEmpty() ? null : result.get(0);
        } catch (Exception e) {
            System.err.println("嵌入生成失败: " + e.getMessage());
            return null;
        }
    }

    private List<List<Double>> generateEmbeddings(List<String> texts) {
        try {
            File script = new File("src/main/scripts/embed.py");
            if (!script.exists()) {
                script = new File("backend-java/src/main/scripts/embed.py");
            }

            ProcessBuilder pb = new ProcessBuilder("python", script.getAbsolutePath());
            Process process = pb.start();

            try (var writer = process.getOutputStream()) {
                objectMapper.writeValue(writer, texts);
            }

            List<List<Double>> result = objectMapper.readValue(process.getInputStream(), new TypeReference<>() {
            });

            if (!process.waitFor(30, TimeUnit.SECONDS)) {
                process.destroy();
                return null;
            }

            return result;
        } catch (Exception e) {
            System.err.println("批量嵌入生成失败: " + e.getMessage());
            return null;
        }
    }

    private String ensureCollection(String collectionName) {
        if (COLLECTION_PRODUCTS.equals(collectionName) && productCollectionId != null)
            return productCollectionId;
        if (COLLECTION_SCRIPTS.equals(collectionName) && scriptCollectionId != null)
            return scriptCollectionId;

        try {
            // 检查集合是否存在
            try {
                Map<String, Object> collection = restTemplate
                        .getForObject(CHROMA_URL + "/collections/" + collectionName, Map.class);
                if (collection != null) {
                    String id = (String) collection.get("id");
                    if (COLLECTION_PRODUCTS.equals(collectionName))
                        productCollectionId = id;
                    else if (COLLECTION_SCRIPTS.equals(collectionName))
                        scriptCollectionId = id;
                    return id;
                }
            } catch (Exception ignored) {
            }

            // 创建集合
            Map<String, Object> request = new HashMap<>();
            request.put("name", collectionName);
            request.put("metadata", Map.of("hnsw:space", "cosine"));

            Map<String, Object> response = restTemplate.postForObject(CHROMA_URL + "/collections", request, Map.class);
            if (response != null) {
                String id = (String) response.get("id");
                if (COLLECTION_PRODUCTS.equals(collectionName))
                    productCollectionId = id;
                else if (COLLECTION_SCRIPTS.equals(collectionName))
                    scriptCollectionId = id;
                return id;
            }
        } catch (Exception e) {
            System.err.println("确保集合存在失败 (" + collectionName + "): " + e.getMessage());
        }
        return null;
    }

    private int ingestMarketingScripts(List<Object> scripts) {
        if (scripts == null || scripts.isEmpty())
            return 0;

        try {
            String colId = ensureCollection(COLLECTION_SCRIPTS);
            if (colId == null)
                return 0;

            List<String> ids = new ArrayList<>();
            List<String> texts = new ArrayList<>();
            List<Map<String, Object>> metadatas = new ArrayList<>();

            for (Object scriptObj : scripts) {
                if (scriptObj instanceof Map<?, ?> raw) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    raw.forEach((k, v) -> item.put(String.valueOf(k), v));

                    String content = getString(item, "content");
                    if (content == null || content.isBlank())
                        continue;

                    String scenario = getString(item, "scenario", "general");
                    String tags = getString(item, "tags", "");

                    String id = UUID.randomUUID().toString();

                    // 向量化文本: [场景] 内容
                    String textToEmbed = String.format("场景: %s. 内容: %s", scenario, content);

                    Map<String, Object> meta = new HashMap<>();
                    meta.put("scenario", scenario);
                    meta.put("tags", tags);

                    ids.add(id);
                    texts.add(textToEmbed);
                    metadatas.add(meta);
                }
            }

            if (!ids.isEmpty()) {
                List<List<Double>> embeddings = generateEmbeddings(texts);
                if (embeddings != null && embeddings.size() == ids.size()) {
                    Map<String, Object> request = new HashMap<>();
                    request.put("ids", ids);
                    request.put("documents", texts);
                    request.put("metadatas", metadatas);
                    request.put("embeddings", embeddings);

                    restTemplate.postForObject(CHROMA_URL + "/collections/" + colId + "/upsert", request, Map.class);
                    return ids.size();
                }
            }
        } catch (Exception e) {
            System.err.println("话术入库失败: " + e.getMessage());
        }
        return 0;
    }

    private List<Map<String, Object>> parseChromaResponse(Map<String, Object> response) {
        List<Map<String, Object>> results = new ArrayList<>();
        if (response == null)
            return results;

        List<List<String>> ids = (List<List<String>>) response.get("ids");
        List<List<Map<String, Object>>> metadatas = (List<List<Map<String, Object>>>) response.get("metadatas");
        List<List<Double>> distances = (List<List<Double>>) response.get("distances");
        // ChromaDB 返回的原始文档 (the actual text)
        List<List<String>> documents = (List<List<String>>) response.get("documents");

        if (ids != null && !ids.isEmpty() && !ids.get(0).isEmpty()) {
            for (int i = 0; i < ids.get(0).size(); i++) {
                Map<String, Object> result = new LinkedHashMap<>();

                // [提取 Metadata]
                // 搜索结果直接包含 metadata 对象，我们把它转换成业务需要的 Map 格式
                // 这样 Agent 就能直接读到结构化的 price, category 等字段，不需要正则去解析 document 文本
                Map<String, Object> meta = metadatas.get(0).get(i);

                result.put("product_id", meta.get("product_id"));
                result.put("name", meta.get("name"));
                result.put("category", meta.get("category"));

                // 如果有 document (原文)，也放进去
                if (documents != null && !documents.isEmpty() && documents.get(0).size() > i) {
                    result.put("content", documents.get(0).get(i));
                }

                try {
                    // [转换 Metadata]
                    // 存储时为了兼容可能转成了 String，这里转回 Double 给业务用
                    Object priceObj = meta.get("price");
                    result.put("price", Double.parseDouble(String.valueOf(priceObj)));
                } catch (Exception e) {
                    result.put("price", 0.0);
                }

                String sellingPointsStr = (String) meta.get("selling_points_str");
                result.put("selling_points", splitSellingPoints(sellingPointsStr));

                if (distances != null && !distances.isEmpty()) {
                    result.put("distance", distances.get(0).get(i));
                }

                results.add(result);
            }
        }
        return results;
    }

    private Map<String, Object> getProductDetails(String productId) {
        if (productId == null || productId.isBlank()) {
            return null;
        }
        List<Map<String, Object>> results = jdbcTemplate.query(
                """
                        SELECT sku_id, name, selling_points, price
                        FROM products
                        WHERE sku_id = ?
                        """,
                (rs, rowNum) -> {
                    Map<String, Object> result = new LinkedHashMap<>();
                    result.put("product_id", rs.getString("sku_id"));
                    result.put("name", rs.getString("name"));
                    result.put("category", null);
                    result.put("price", rs.getBigDecimal("price"));
                    result.put("selling_points", splitSellingPoints(rs.getString("selling_points")));
                    return result;
                },
                productId);
        return results.isEmpty() ? null : results.getFirst();
    }

    private Map<String, Object> syncMysqlToVector() {
        try {
            // 从 MySQL 获取所有商品
            List<Map<String, Object>> products = jdbcTemplate.queryForList("SELECT * FROM products");
            if (products.isEmpty()) {
                return Map.of("status", "skipped", "message", "No products found in MySQL");
            }

            // 转换数据格式以匹配 ingestProductKnowledge 的输入要求
            List<Object> normalizedProducts = products.stream().map(row -> {
                Map<String, Object> item = new HashMap<>();
                item.put("id", row.get("sku_id"));
                item.put("name", row.get("name"));
                item.put("category", row.get("category"));
                item.put("price", row.get("price"));
                item.put("description", row.get("description"));

                // 处理 selling_points (可能是 JSON 字符串或普通字符串)
                Object sp = row.get("selling_points");
                if (sp instanceof String spStr) {
                    item.put("selling_points", splitSellingPoints(spStr));
                } else {
                    item.put("selling_points", List.of());
                }

                return (Object) item;
            }).toList();

            // 复用 ingestProductKnowledge 的逻辑写入 ChromaDB
            // 注意：ingestProductKnowledge 内部会再次尝试写入 MySQL，但因为是 INSERT IGNORE 或 ON DUPLICATE
            // KEY UPDATE (取决于具体实现)，所以是安全的
            // 为了避免重复写入 MySQL，我们可以稍微重构 ingestProductKnowledge，或者接受这点性能开销
            // 这里为了简单，我们直接调用，因为重点是向量化

            // 实际上，ingestProductKnowledge 第一步是写入 MySQL。
            // 如果我们只想同步到向量库，应该拆分逻辑。
            // 下面是专门针对向量库的同步逻辑 (复用 ingestToVector 部分)

            int count = ingestToVectorOnly(normalizedProducts);

            return Map.of("status", "success", "count", count);
        } catch (Exception e) {
            return Map.of("status", "error", "message", e.getMessage());
        }
    }

    private int ingestToVectorOnly(List<Object> products) {
        if (products == null || products.isEmpty()) {
            return 0;
        }

        try {
            String colId = ensureCollection(COLLECTION_PRODUCTS);
            if (colId == null) {
                return 0;
            }

            List<String> ids = new ArrayList<>();
            List<String> texts = new ArrayList<>();
            List<Map<String, Object>> metadatas = new ArrayList<>();

            for (Object productObj : products) {
                if (productObj instanceof Map<?, ?> raw) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    raw.forEach((k, v) -> item.put(String.valueOf(k), v));

                    String id = getString(item, "id", getString(item, "sku_id"));
                    String name = getString(item, "name");
                    String desc = getString(item, "description", "");
                    String category = getString(item, "category", "");
                    Double price = getDouble(item, "price", 0.0);
                    List<String> sellingPoints = getList(item, "selling_points").stream().map(String::valueOf).toList();
                    String sellingPointsStr = String.join("; ", sellingPoints);

                    // 构建语义丰富的文本 (Rich Semantic Text) - 中文优化版
                    // 仅使用最核心的词汇，避免噪声干扰
                    String priceTier;
                    if (price < 100) {
                        priceTier = "便宜 Affordable";
                    } else if (price >= 100 && price <= 300) {
                        priceTier = "性价比 Standard";
                    } else if (price > 500) {
                        priceTier = "昂贵 Expensive";
                    } else {
                        priceTier = "中等 Moderate";
                    }

                    // 增强卖点描述 (中文优先)
                    String enhancedSellingPoints = sellingPointsStr;
                    if (desc.toLowerCase().contains("new") || desc.contains("新品")) {
                        enhancedSellingPoints += " 新品 New";
                    }
                    if (desc.toLowerCase().contains("limited") || desc.contains("限量")) {
                        enhancedSellingPoints += " 限量 Limited";
                    }
                    if (desc.toLowerCase().contains("sale") || desc.contains("discount") || desc.contains("off")) {
                        enhancedSellingPoints += " 特价 Sale";
                    }

                    // 组合最终的向量化文本 (中文模板)
                    String text = String.format(
                            "分类: %s. 商品: %s. 价格等级: %s. 特点: %s. 描述: %s",
                            category, name, priceTier, enhancedSellingPoints, desc);

                    // [存储 Metadata]
                    // 将结构化字段存入 metadata map，ChromaDB 会随向量一起存储
                    // 作用：
                    // 1. 结果解析：搜索回来后，不需要解析长文本，直接读字段
                    // 2. 精确过滤：支持 where={"price": {"$lt": 500}} 这种查询
                    Map<String, Object> metadata = new HashMap<>();
                    metadata.put("product_id", id);
                    metadata.put("name", name);
                    metadata.put("category", category);
                    metadata.put("price", String.valueOf(price)); // 存为字符串以兼容
                    metadata.put("selling_points_str", sellingPointsStr);

                    ids.add(id);
                    texts.add(text);
                    metadatas.add(metadata);
                }
            }

            if (!ids.isEmpty()) {
                // 批量生成嵌入向量
                List<List<Double>> embeddings = generateEmbeddings(texts);

                if (embeddings != null && embeddings.size() == ids.size()) {
                    Map<String, Object> request = new HashMap<>();
                    request.put("ids", ids);
                    request.put("documents", texts);
                    request.put("metadatas", metadatas);
                    request.put("embeddings", embeddings);

                    restTemplate.postForObject(CHROMA_URL + "/collections/" + colId + "/upsert", request,
                            Map.class);
                    return ids.size();
                }
            }
        } catch (Exception e) {
            System.err.println("向量同步失败: " + e.getMessage());
        }
        return 0;
    }

    private int ingestProductKnowledge(List<Object> products) {
        if (products == null || products.isEmpty()) {
            return 0;
        }

        // 1. 写入 MySQL (数据源)
        int mysqlCount = ingestToMysql(products);

        // 2. 写入 ChromaDB (向量索引)
        // 复用 ingestToVectorOnly 逻辑
        ingestToVectorOnly(products);

        return mysqlCount;
    }

    private int ingestToMysql(List<Object> products) {
        List<Map<String, Object>> normalized = new ArrayList<>();
        for (Object productObj : products) {
            if (productObj instanceof Map<?, ?> raw) {
                Map<String, Object> mapped = new LinkedHashMap<>();
                raw.forEach((k, v) -> mapped.put(String.valueOf(k), v));
                normalized.add(mapped);
            }
        }
        if (normalized.isEmpty()) {
            return 0;
        }
        String sql = """
                INSERT INTO products (sku_id, name, selling_points, price, stock)
                VALUES (?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    selling_points = VALUES(selling_points),
                    price = VALUES(price),
                    stock = VALUES(stock)
                """;
        List<Object[]> batchArgs = normalized.stream().map(item -> new Object[] {
                getString(item, "id", getString(item, "sku_id")),
                getString(item, "name"),
                normalizeSellingPoints(item.get("selling_points")),
                getDouble(item, "price", 0.0),
                getInt(item, "stock", 0)
        }).filter(args -> args[0] != null).collect(Collectors.toList());
        if (batchArgs.isEmpty()) {
            return 0;
        }
        int[] results = jdbcTemplate.batchUpdate(sql, batchArgs);
        return results.length;
    }

    private Map<String, Object> sendSms(String userId, String phone, String message) {
        if (userId == null || userId.isBlank() || phone == null || phone.isBlank() || message == null
                || message.isBlank()) {
            throw new IllegalArgumentException("send_sms requires user_id, phone, message");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", true);
        result.put("user_id", userId);
        result.put("phone", phone);
        result.put("message", message);
        result.put("timestamp", OffsetDateTime.now(ZoneOffset.UTC).toString());
        result.put("action", "SMS_SENT");
        return result;
    }

    private Map<String, Object> skipMarketing(String userId, String reason) {
        if (userId == null || userId.isBlank() || reason == null || reason.isBlank()) {
            throw new IllegalArgumentException("skip_marketing requires user_id, reason");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", true);
        result.put("user_id", userId);
        result.put("reason", reason);
        result.put("timestamp", OffsetDateTime.now(ZoneOffset.UTC).toString());
        result.put("action", "SKIP_MARKETING");
        return result;
    }

    private List<String> parseTags(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            return objectMapper.readValue(raw, new TypeReference<>() {
            });
        } catch (Exception e) {
            return List.of();
        }
    }

    private List<String> splitSellingPoints(String sellingPoints) {
        if (sellingPoints == null || sellingPoints.isBlank()) {
            return List.of();
        }
        String normalized = sellingPoints.replace("；", ";").replace(",", ";");
        return Arrays.stream(normalized.split(";"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .toList();
    }

    private String normalizeSellingPoints(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof String str) {
            return str;
        }
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).collect(Collectors.joining("; "));
        }
        return String.valueOf(value);
    }

    // 辅助方法
    private Long parseUserId(String userId) {
        try {
            return Long.parseLong(userId);
        } catch (Exception e) {
            // 如果格式是 "user-123"，尝试提取数字
            if (userId != null && userId.contains("-")) {
                try {
                    return Long.parseLong(userId.split("-")[1]);
                } catch (Exception ex) {
                    return null;
                }
            }
            return null;
        }
    }

    private String getString(Map<String, Object> args, String key) {
        return args.get(key) != null ? String.valueOf(args.get(key)) : null;
    }

    private String getString(Map<String, Object> args, String key, String defaultValue) {
        return args.get(key) != null ? String.valueOf(args.get(key)) : defaultValue;
    }

    private int getInt(Map<String, Object> args, String key, int defaultValue) {
        Object val = args.get(key);
        if (val instanceof Number n)
            return n.intValue();
        if (val instanceof String s) {
            try {
                return Integer.parseInt(s);
            } catch (NumberFormatException e) {
                return defaultValue;
            }
        }
        return defaultValue;
    }

    private double getDouble(Map<String, Object> args, String key, double defaultValue) {
        Object val = args.get(key);
        if (val instanceof Number n)
            return n.doubleValue();
        if (val instanceof String s) {
            try {
                return Double.parseDouble(s);
            } catch (NumberFormatException e) {
                return defaultValue;
            }
        }
        return defaultValue;
    }

    private List<Object> getList(Map<String, Object> args, String key) {
        Object val = args.get(key);
        if (val instanceof List<?>)
            return (List<Object>) val;
        return List.of();
    }

    // 模式生成器
    private Map<String, Object> schema(Map<String, Object> properties, List<String> required) {
        Map<String, Object> schema = new LinkedHashMap<>();
        schema.put("type", "object");
        schema.put("properties", properties);
        if (required != null && !required.isEmpty()) {
            schema.put("required", required);
        }
        return schema;
    }
}
