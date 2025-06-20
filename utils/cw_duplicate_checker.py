#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クラウドワークス重複IDチェッカー
実験参加者の調査IDの重複をチェックするためのスクレイピングツール
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import json
from datetime import datetime
from collections import Counter
import re
import argparse

class CrowdWorksIDChecker:
    def __init__(self, session_cookie=None):
        """
        初期化
        Args:
            session_cookie (str): ログイン済みのセッションクッキー
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if session_cookie:
            self.session.cookies.update({'session': session_cookie})
    
    def extract_ids_from_text(self, text):
        """
        テキストから調査IDを抽出する
        Args:
            text (str): 抽出対象のテキスト
        Returns:
            list: 抽出されたIDのリスト
        """
        # 10桁以上の数字、または英数字の組み合わせを調査IDとして抽出
        patterns = [
            r'\b\d{10,}\b',  # 10桁以上の数字
            r'\b[A-Za-z0-9]{10,}\b',  # 10文字以上の英数字
            r'ID[:\s]*([A-Za-z0-9]{8,})',  # ID: で始まる8文字以上
            r'調査ID[:\s]*([A-Za-z0-9]{8,})',  # 調査ID: で始まる
        ]
        
        ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ids.extend(matches)
        
        # 重複を除去して返す
        return list(set(ids))
    
    def scrape_submission_data(self, project_url, max_pages=10):
        """
        プロジェクトの提出データを取得
        Args:
            project_url (str): プロジェクトのURL
            max_pages (int): 最大取得ページ数
        Returns:
            list: 提出データのリスト
        """
        submissions = []
        
        for page in range(1, max_pages + 1):
            print(f"ページ {page} を取得中...")
            
            # ページURLを構築
            page_url = f"{project_url}?page={page}"
            
            try:
                response = self.session.get(page_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 提出データを抽出（実際のHTML構造に応じて調整が必要）
                submission_items = soup.find_all('div', class_='submission-item')
                
                if not submission_items:
                    print(f"ページ {page} に提出データが見つかりません。終了します。")
                    break
                
                for item in submission_items:
                    # ワーカー名を取得
                    worker_element = item.find('a', class_='worker-name')
                    worker_name = worker_element.text.strip() if worker_element else "不明"
                    
                    # 提出内容を取得
                    content_element = item.find('div', class_='submission-content')
                    content = content_element.text.strip() if content_element else ""
                    
                    # 提出日時を取得
                    date_element = item.find('span', class_='submission-date')
                    submission_date = date_element.text.strip() if date_element else ""
                    
                    # 調査IDを抽出
                    extracted_ids = self.extract_ids_from_text(content)
                    
                    submission_data = {
                        'worker_name': worker_name,
                        'content': content,
                        'submission_date': submission_date,
                        'extracted_ids': extracted_ids,
                        'page': page
                    }
                    
                    submissions.append(submission_data)
                
                # レート制限回避のための待機
                time.sleep(1)
                
            except requests.RequestException as e:
                print(f"ページ {page} の取得でエラー: {e}")
                break
        
        return submissions
    
    def analyze_duplicates(self, submissions):
        """
        重複IDを分析
        Args:
            submissions (list): 提出データのリスト
        Returns:
            dict: 分析結果
        """
        all_ids = []
        id_to_workers = {}
        worker_to_ids = {}
        
        for submission in submissions:
            worker = submission['worker_name']
            
            for survey_id in submission['extracted_ids']:
                all_ids.append(survey_id)
                
                # IDからワーカーへのマッピング
                if survey_id not in id_to_workers:
                    id_to_workers[survey_id] = []
                id_to_workers[survey_id].append({
                    'worker': worker,
                    'date': submission['submission_date'],
                    'content': submission['content'][:100]  # 最初の100文字のみ
                })
                
                # ワーカーからIDへのマッピング
                if worker not in worker_to_ids:
                    worker_to_ids[worker] = []
                worker_to_ids[worker].append(survey_id)
        
        # 重複IDを特定
        id_counts = Counter(all_ids)
        duplicate_ids = {id_val: count for id_val, count in id_counts.items() if count > 1}
        
        # 疑わしいワーカーを特定（同じIDを複数回使用）
        suspicious_workers = {}
        for worker, ids in worker_to_ids.items():
            id_counts_per_worker = Counter(ids)
            repeated_ids = {id_val: count for id_val, count in id_counts_per_worker.items() if count > 1}
            if repeated_ids:
                suspicious_workers[worker] = repeated_ids
        
        return {
            'total_submissions': len(submissions),
            'total_ids': len(all_ids),
            'unique_ids': len(set(all_ids)),
            'duplicate_ids': duplicate_ids,
            'id_to_workers': id_to_workers,
            'worker_to_ids': worker_to_ids,
            'suspicious_workers': suspicious_workers
        }
    
    def generate_report(self, analysis, output_file=None):
        """
        分析結果のレポートを生成
        Args:
            analysis (dict): 分析結果
            output_file (str): 出力ファイル名
        """
        report = []
        report.append("=" * 60)
        report.append("クラウドワークス 重複IDチェック レポート")
        report.append("=" * 60)
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基本統計
        report.append("【基本統計】")
        report.append(f"総提出数: {analysis['total_submissions']}")
        report.append(f"総ID数: {analysis['total_ids']}")
        report.append(f"ユニークID数: {analysis['unique_ids']}")
        report.append(f"重複ID数: {len(analysis['duplicate_ids'])}")
        report.append("")
        
        # 重複IDの詳細
        if analysis['duplicate_ids']:
            report.append("【重複ID一覧】")
            for survey_id, count in analysis['duplicate_ids'].items():
                report.append(f"ID: {survey_id} (使用回数: {count}回)")
                workers = analysis['id_to_workers'][survey_id]
                for worker_info in workers:
                    report.append(f"  - ワーカー: {worker_info['worker']} (日時: {worker_info['date']})")
            report.append("")
        
        # 疑わしいワーカー
        if analysis['suspicious_workers']:
            report.append("【疑わしいワーカー（同一IDを複数回使用）】")
            for worker, repeated_ids in analysis['suspicious_workers'].items():
                report.append(f"ワーカー: {worker}")
                for survey_id, count in repeated_ids.items():
                    report.append(f"  - ID: {survey_id} を {count}回使用")
            report.append("")
        
        # 推奨アクション
        report.append("【推奨アクション】")
        if analysis['duplicate_ids']:
            report.append("1. 重複IDを使用している提出を確認")
            report.append("2. 疑わしいワーカーの他の提出も調査")
            report.append("3. 明らかな不正は非承認処理")
        else:
            report.append("重複IDは検出されませんでした。")
        
        report_text = "\n".join(report)
        
        # ファイル出力
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"レポートを {output_file} に保存しました。")
        
        return report_text
    
    def export_csv(self, submissions, analysis, filename):
        """
        CSVファイルにデータをエクスポート
        Args:
            submissions (list): 提出データ
            analysis (dict): 分析結果
            filename (str): 出力ファイル名
        """
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['worker_name', 'submission_date', 'extracted_ids', 'is_duplicate', 'content_preview']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for submission in submissions:
                for survey_id in submission['extracted_ids']:
                    is_duplicate = survey_id in analysis['duplicate_ids']
                    writer.writerow({
                        'worker_name': submission['worker_name'],
                        'submission_date': submission['submission_date'],
                        'extracted_ids': survey_id,
                        'is_duplicate': 'YES' if is_duplicate else 'NO',
                        'content_preview': submission['content'][:200]
                    })
        
        print(f"CSVデータを {filename} に保存しました。")

def main():
    parser = argparse.ArgumentParser(description='クラウドワークス重複IDチェッカー')
    parser.add_argument('project_url', help='プロジェクトのURL')
    parser.add_argument('--max-pages', type=int, default=10, help='最大取得ページ数 (デフォルト: 10)')
    parser.add_argument('--output', help='レポート出力ファイル名')
    parser.add_argument('--csv', help='CSV出力ファイル名')
    parser.add_argument('--session-cookie', help='ログイン済みセッションクッキー')
    
    args = parser.parse_args()
    
    # チェッカーを初期化
    checker = CrowdWorksIDChecker(session_cookie=args.session_cookie)
    
    print("クラウドワークス重複IDチェッカーを開始します...")
    print(f"対象URL: {args.project_url}")
    print(f"最大取得ページ数: {args.max_pages}")
    print()
    
    # データを取得
    submissions = checker.scrape_submission_data(args.project_url, args.max_pages)
    
    if not submissions:
        print("提出データが見つかりませんでした。")
        return
    
    print(f"取得した提出数: {len(submissions)}")
    
    # 重複を分析
    analysis = checker.analyze_duplicates(submissions)
    
    # レポートを生成
    output_file = args.output or f"duplicate_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = checker.generate_report(analysis, output_file)
    
    # CSVエクスポート
    if args.csv:
        checker.export_csv(submissions, analysis, args.csv)
    
    # 結果を表示
    print("\n" + report)
    
    if analysis['duplicate_ids']:
        print(f"\n⚠️  {len(analysis['duplicate_ids'])} 個の重複IDが検出されました！")
    else:
        print("\n✅ 重複IDは検出されませんでした。")

if __name__ == '__main__':
    main()
