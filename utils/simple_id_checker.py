#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シンプル重複IDチェッカー
テキストファイルまたは手動入力から重複IDをチェックする軽量版ツール
"""

import re
from collections import Counter
from datetime import datetime
import argparse

def extract_ids_from_text(text):
    """
    テキストから調査IDを抽出
    """
    # 一般的なIDパターン
    patterns = [
        r'\b\d{10,}\b',  # 10桁以上の数字
        r'\b[A-Za-z0-9]{10,}\b',  # 10文字以上の英数字
        r'(?:ID|調査ID)[:\s]*([A-Za-z0-9]{8,})',  # ID:または調査ID:で始まる
    ]
    
    ids = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if isinstance(matches[0], tuple) if matches else False:
            ids.extend([match[0] if match else match for match in matches])
        else:
            ids.extend(matches)
    
    return ids

def check_duplicates_from_text(text_data):
    """
    テキストデータから重複IDをチェック
    """
    all_ids = []
    
    # 行ごとに処理
    lines = text_data.strip().split('\n')
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        extracted_ids = extract_ids_from_text(line)
        for survey_id in extracted_ids:
            all_ids.append({
                'id': survey_id,
                'line_number': i,
                'line_content': line[:100]  # 最初の100文字
            })
    
    # 重複分析
    id_counts = Counter([item['id'] for item in all_ids])
    duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}
    
    return {
        'total_ids': len(all_ids),
        'unique_ids': len(set([item['id'] for item in all_ids])),
        'duplicates': duplicates,
        'all_ids': all_ids
    }

def generate_simple_report(analysis):
    """
    シンプルなレポートを生成
    """
    report = []
    report.append("=" * 50)
    report.append("重複IDチェック結果")
    report.append("=" * 50)
    report.append(f"検査日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    report.append("【統計】")
    report.append(f"総ID数: {analysis['total_ids']}")
    report.append(f"ユニークID数: {analysis['unique_ids']}")
    report.append(f"重複ID数: {len(analysis['duplicates'])}")
    report.append("")
    
    if analysis['duplicates']:
        report.append("【重複ID詳細】")
        for survey_id, count in analysis['duplicates'].items():
            report.append(f"🚨 ID: {survey_id} (出現回数: {count})")
            
            # この IDが出現した行を表示
            matching_items = [item for item in analysis['all_ids'] if item['id'] == survey_id]
            for item in matching_items:
                report.append(f"   行{item['line_number']}: {item['line_content']}")
            report.append("")
    else:
        report.append("✅ 重複IDは見つかりませんでした")
    
    return "\n".join(report)

def interactive_mode():
    """
    対話的モード
    """
    print("=== シンプル重複IDチェッカー ===")
    print("IDを含むテキストを入力してください。")
    print("（完了するには空行で 'END' と入力）")
    print()
    
    lines = []
    while True:
        try:
            line = input("> ")
            if line.strip().upper() == 'END':
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\n中断されました。")
            return
    
    if not lines:
        print("入力がありませんでした。")
        return
    
    text_data = '\n'.join(lines)
    analysis = check_duplicates_from_text(text_data)
    report = generate_simple_report(analysis)
    
    print("\n" + report)

def main():
    parser = argparse.ArgumentParser(description='シンプル重複IDチェッカー')
    parser.add_argument('--file', help='チェックするテキストファイル')
    parser.add_argument('--output', help='結果出力ファイル')
    parser.add_argument('--interactive', action='store_true', help='対話的モード')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text_data = f.read()
        except FileNotFoundError:
            print(f"ファイルが見つかりません: {args.file}")
            return
        except Exception as e:
            print(f"ファイル読み込みエラー: {e}")
            return
    else:
        print("ファイルが指定されていません。--interactive オプションを使用するか、--file でファイルを指定してください。")
        return
    
    # 分析実行
    analysis = check_duplicates_from_text(text_data)
    report = generate_simple_report(analysis)
    
    # 結果出力
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"結果を {args.output} に保存しました。")
    
    print(report)

if __name__ == '__main__':
    main()
