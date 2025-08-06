"""
crt_cluster_histogram_analysis.py

CRTクラスター別ヒストグラム分析専用スクリプト
"""
from correlation_analysis_extended import CorrelationAnalyzer

def main():
    """CRTクラスター分析を実行"""
    print("=== CRTクラスター分析 ===")
    print("=" * 50)
    
    analyzer = CorrelationAnalyzer("final_valid_updated.csv", max_k=5)
    
    # 複数のthreshold値でCRTクラスターヒストグラムを作成
    thresholds_to_analyze = [1.0, 0.5, 0.1]
    
    print(f"分析するthreshold値: {thresholds_to_analyze}")
    
    # CRTクラスターヒストグラムを作成
    print("\n=== CRTクラスターヒストグラム作成 ===")
    analyzer.create_crt_cluster_histograms(thresholds_to_analyze)
    
    # CRTクラスター要約統計量テーブル作成
    print("\n=== CRTクラスター要約統計量テーブル作成 ===")
    crt_cluster_summary = analyzer.create_crt_cluster_summary_table(thresholds_to_analyze)
    
    print("\n=== CRTクラスター分析完了 ===")

if __name__ == "__main__":
    main()
