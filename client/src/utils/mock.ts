/** 原型示例数据（Redis 案例）：USE_MOCK 模式与首页快捷标签使用 */

import type { KnowledgeExtraction, PublicQuiz, Report } from '@/types'

export const HOT_TOPICS = ['Redis 缓存机制', 'Spring Boot 自动配置', 'TCP 三次握手', 'JVM 垃圾回收', 'MySQL 索引原理']

export const MOCK_EXTRACTION: KnowledgeExtraction = {
  topic: 'Redis 缓存机制',
  summary: 'Redis 缓存三大问题（穿透/击穿/雪崩）及解决方案，常用数据结构。',
  knowledge_points: [
    { name: '缓存穿透', definition: '查询不存在的数据导致缓存与数据库均miss', importance: 5, confusion_with: ['缓存击穿'] },
    { name: '缓存击穿', definition: '热点key失效瞬间大量请求打到数据库', importance: 5, confusion_with: ['缓存穿透', '缓存雪崩'] },
    { name: '缓存雪崩', definition: '大量key同时过期或Redis宕机', importance: 4, confusion_with: ['缓存击穿'] },
    { name: '布隆过滤器', definition: '拦截非法key的概率型数据结构', importance: 3, confusion_with: [] },
    { name: 'ZSet 与跳表', definition: 'ZSet 底层使用跳表实现有序集合', importance: 3, confusion_with: [] },
  ],
}

export const MOCK_QUIZ: PublicQuiz = {
  quiz_id: 'quiz_mock01',
  title: 'Redis 缓存闯关',
  questions: [
    {
      index: 0, type: 'single_choice', difficulty: 2, knowledge_point: '缓存穿透',
      stem: '缓存穿透指的是以下哪种情况？',
      options: ['查询数据库中根本不存在的数据，缓存和数据库都miss', '热点key过期瞬间大量请求打到数据库', '大量key在同一时间过期', 'Redis主从切换导致数据丢失'],
    },
    {
      index: 1, type: 'single_choice', difficulty: 3, knowledge_point: '缓存击穿',
      stem: '应对缓存击穿的常见方案是什么？',
      options: ['给过期时间加随机值', '使用互斥锁保证只有一个线程回源', '使用布隆过滤器', '清空全部缓存'],
    },
    {
      index: 2, type: 'single_choice', difficulty: 4, knowledge_point: 'ZSet 与跳表',
      stem: 'ZSet 底层使用什么数据结构实现有序集合？',
      options: ['跳表', '红黑树', 'B+树', '哈希表'],
    },
    {
      index: 3, type: 'true_false', difficulty: 1, knowledge_point: '布隆过滤器',
      stem: '布隆过滤器可以用于拦截缓存穿透中的非法key。',
      options: ['正确', '错误'],
    },
    {
      index: 4, type: 'scenario', difficulty: 4, knowledge_point: '缓存击穿',
      stem: '秒杀活动开始前一秒，商品详情 key 恰好过期，8 万 QPS 全部落到 MySQL，数据库 CPU 打满。你第一步应该做什么？',
      options: ['立即扩容 MySQL 只读从库，把读流量分摊出去', '用分布式互斥锁只放一个请求重建缓存，其余请求短暂等待', '把商品详情改为永不过期，避免再次失效', '给所有 key 的过期时间加上随机值'],
    },
  ],
  gamification: { exp: 120, combo: 0, quota_remaining: 29 },
}

export const MOCK_ANSWERS: Record<number, { correct_answer: number; explanation: string; source_excerpt: string }> = {
  0: { correct_answer: 0, explanation: '缓存穿透查询的是数据库中根本不存在的数据，缓存与库都挡不住。', source_excerpt: '缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss' },
  1: { correct_answer: 1, explanation: '互斥锁把重建缓存串行化，只放一个请求回源，是击穿场景最快的止血动作。', source_excerpt: '缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库' },
  2: { correct_answer: 0, explanation: 'ZSet 底层使用跳表（skiplist）实现有序集合。', source_excerpt: 'ZSet底层使用跳表实现有序集合' },
  3: { correct_answer: 0, explanation: '布隆过滤器可拦截一定不存在的 key，是穿透防护的常见手段。', source_excerpt: '解决方案是使用布隆过滤器拦截非法key' },
  4: { correct_answer: 1, explanation: '热点 key 失效瞬间被并发打穿是典型击穿，互斥锁重建是最快止血动作。', source_excerpt: '缓存击穿是指某个热点key在过期失效的瞬间，大量并发请求同时打到数据库' },
}

export const MOCK_SCENARIO_LOG = `2026-09-15 20:59:59  WARN  HikariPool-1 - Connection is not available
2026-09-15 21:00:00  ERROR ProductDao - select timeout after 3000ms
redis: GET product:1001 -> (nil)   x 81204 / s`

export const MOCK_REPORT: Report = {
  quiz_id: 'quiz_mock01',
  client_id: 'mock',
  title: 'Redis 缓存闯关',
  score: 80,
  accuracy: 0.8,
  duration_ms: 214000,
  mastery_levels: { 缓存穿透: 'good', 缓存击穿: 'weak', 布隆过滤器: 'good', 'ZSet 与跳表': 'good' },
  wrong_questions: [
    { index: 1, stem: '应对缓存击穿的常见方案是什么？', error_type: '概念混淆', analysis: '把缓存击穿与缓存雪崩的解决方案混淆：击穿用互斥锁重建，雪崩才靠过期时间加随机值。' },
  ],
  performance_summary: '本次闯关对缓存三大问题的整体掌握不错，但击穿的解决方案仍需巩固。',
  confusion_pairs: ['缓存击穿 vs 缓存雪崩：前者是单个热点 key 失效，后者是大量 key 集中失效或实例宕机'],
  suggestions: [
    '把穿透、击穿、雪崩的触发条件和解法做成一张对照表，各记一句话',
    '针对缓存击穿单独练 3 道场景题，重点是互斥锁重建与逻辑过期的取舍',
    '明天这个时间回来复习薄弱点，5 题即可',
  ],
  ai_generated: true,
  badges: ['first_quiz'],
  exp_gained: 120,
  created_at: new Date().toISOString(),
}
