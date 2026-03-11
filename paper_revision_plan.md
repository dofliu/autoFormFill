# 論文修訂計畫
## Paper: Semantic Richness Over Domain Matching (APIN-D-26-00778)

**被拒原因：** "The article does not have sufficient material in terms of novelty and technical quality"

---

## 核心策略

**將論文從「經驗性研究」轉為「指標 + 決策框架論文」**

這直接解決了「 novelty 不足」的問題。

---

## 單一最具影響力的改變

引入 **Semantic Richness Score (SRS)** 作為正式定義的指標！

這給論文一個具體的、可引用 的貢獻，而不僅僅是發現。

---

## 標題建議

> **A Decision Framework for Cross-Source Transfer in Industrial RAG Systems: Semantic Richness Outperforms Domain Matching**

---

## 提交前必須做的

### 1. 統計顯著性測試
- 對所有 MRR 比較添加配對 t 檢定
- 計算 Cohen's d 和 95% 信賴區間

### 2. 添加 BM25 基線
- 審稿人一定會問這個！

### 3. 正式定義 SRS
- 作為編號的、命名的貢獻

### 4. 添加消融實驗
- 解決雙語 vs 語料庫大小的混雜變數
- 對 Manufacturer B 進行降採樣以匹配 A 的大小

### 5. 重寫貢獻部分
- 明確強調 novelty

---

## 目標期刊順序

1. **Expert Systems with Applications** (IF ~8.5) 
   - 最佳契合，「框架」論述完全符合

2. **Engineering Applications of AI** (IF ~8.0) 
   - 安全關鍵角度完美契合

3. **IEEE Transactions on Industrial Informatics** (IF ~12.3) 
   - 完成消融實驗後再投

---

## 關鍵框架轉變

**現在：**
> 「我們做了一個實驗，發現了...」

**應該變成：**
> 「我們提出 SRS 並驗證了它...」

---

## 具體修改建議

### 標題
- 移除 "Empirical Investigation"
- 加入 "Framework" 或 "Benchmark"

### 摘要
- 強調決策框架貢獻
- 強調安全關鍵 (+48.2%) 是關鍵差異化
- 加入「實務影響」句子

### 引言
- 強化研究問題（使其更有說服力）
- 加入「為什麼是現在」的論證
- 使貢獻聽起來更創新

### 新穎性聲明
- 提出「Semantic Richness Score (SRS)」指標
- 框架為「實務決策框架」而非僅僅是經驗研究
