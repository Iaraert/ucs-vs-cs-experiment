#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高度スクリーニングシステム
第1段階: 自動スクリーニング（リスクスコア計算）
第2段階: 重複ID・デバイス重複チェック
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import hashlib
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import argparse
from urllib.parse import urlparse
import sqlite3
import os

class AdvancedScreeningSystem:
    def __init__(self, session_cookie=None, db_path=None):
        """
        高度スクリーニングシステムの初期化
        
        Args:
            session_cookie (str): ログイン済みのセッションクッキー
            db_path (str): スクリーニングデータベースのパス
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if session_cookie:
            self.session.cookies.update({'session': session_cookie})
        
        # データベース設定
        self.db_path = db_path or os.path.join('.', 'data', 'screening_database.db')
        self.init_screening_db()
        
        # リスクスコア計算の重み設定
        self.risk_weights = {
            'account_age': 0.15,        # アカウント年数
            'completion_rate': 0.20,    # 完了率
            'profile_quality': 0.15,    # プロフィール充実度
            'rating_history': 0.15,     # 評価履歴
            'submission_pattern': 0.20, # 提出パターン異常
            'device_fingerprint': 0.15  # デバイス指紋異常
        }
        
        # 閾値設定
        self.risk_thresholds = {
            'low': 30,      # 低リスク: 30以下
            'medium': 60,   # 中リスク: 31-60
            'high': 80,     # 高リスク: 61-80
            'critical': 100 # 危険: 81以上
        }

    def init_screening_db(self):
        """スクリーニング用データベースの初期化"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ワーカー情報テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            worker_id TEXT PRIMARY KEY,
            worker_name TEXT NOT NULL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_submissions INTEGER DEFAULT 0,
            risk_score REAL DEFAULT 0,
            risk_level TEXT DEFAULT 'unknown',
            is_flagged BOOLEAN DEFAULT FALSE,
            is_blacklisted BOOLEAN DEFAULT FALSE,
            notes TEXT
        )
        ''')
        
        # 提出データテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id TEXT NOT NULL,
            project_id TEXT,
            submission_date TIMESTAMP,
            survey_id TEXT,
            content_hash TEXT,
            device_fingerprint TEXT,
            ip_hash TEXT,
            user_agent_hash TEXT,
            risk_factors TEXT,
            FOREIGN KEY (worker_id) REFERENCES workers (worker_id)
        )
        ''')
        
        # デバイス指紋テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint_hash TEXT NOT NULL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            worker_count INTEGER DEFAULT 1,
            associated_workers TEXT,
            is_suspicious BOOLEAN DEFAULT FALSE
        )
        ''')
        
        # 重複IDテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id TEXT NOT NULL,
            worker_count INTEGER DEFAULT 1,
            first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            associated_workers TEXT,
            risk_level TEXT DEFAULT 'medium'
        )
        ''')
        
        conn.commit()
        conn.close()

    def extract_worker_profile_data(self, worker_element):
        """
        ワーカープロフィールデータを抽出
        
        Args:
            worker_element: BeautifulSoupの要素
            
        Returns:
            dict: プロフィールデータ
        """
        profile_data = {
            'account_age_days': 0,
            'completion_rate': 0,
            'total_projects': 0,
            'rating': 0,
            'profile_completeness': 0,
            'verification_status': False
        }
        
        try:
            # アカウント作成日の推定（これは実際のHTML構造に依存）
            date_element = worker_element.find('span', class_='member-since')
            if date_element:
                date_text = date_element.text.strip()
                # 日付パースロジック（フォーマットに応じて調整が必要）
                # 例: "2023年1月" -> 推定日数計算
                profile_data['account_age_days'] = self.parse_account_age(date_text)
            
            # 完了率
            completion_element = worker_element.find('span', class_='completion-rate')
            if completion_element:
                rate_text = completion_element.text.strip()
                profile_data['completion_rate'] = self.parse_percentage(rate_text)
            
            # 総プロジェクト数
            projects_element = worker_element.find('span', class_='total-projects')
            if projects_element:
                profile_data['total_projects'] = self.parse_number(projects_element.text.strip())
            
            # 評価
            rating_element = worker_element.find('span', class_='rating')
            if rating_element:
                profile_data['rating'] = self.parse_rating(rating_element.text.strip())
            
            # プロフィール充実度（推定）
            profile_data['profile_completeness'] = self.estimate_profile_completeness(worker_element)
            
        except Exception as e:
            print(f"プロフィールデータ抽出エラー: {e}")
        
        return profile_data

    def calculate_risk_score(self, worker_data, submission_data):
        """
        ワーカーのリスクスコアを計算
        
        Args:
            worker_data (dict): ワーカーの基本データ
            submission_data (dict): 提出データ
            
        Returns:
            dict: リスクスコアと詳細
        """
        risk_factors = {}
        
        # 1. アカウント年数リスク（新しいアカウントほど高リスク）
        account_age_days = worker_data.get('account_age_days', 0)
        if account_age_days < 30:
            risk_factors['account_age'] = 100
        elif account_age_days < 90:
            risk_factors['account_age'] = 70
        elif account_age_days < 365:
            risk_factors['account_age'] = 40
        else:
            risk_factors['account_age'] = 10
        
        # 2. 完了率リスク（低い完了率は高リスク）
        completion_rate = worker_data.get('completion_rate', 0)
        if completion_rate < 50:
            risk_factors['completion_rate'] = 80
        elif completion_rate < 70:
            risk_factors['completion_rate'] = 60
        elif completion_rate < 90:
            risk_factors['completion_rate'] = 30
        else:
            risk_factors['completion_rate'] = 10
        
        # 3. プロフィール品質リスク
        profile_quality = worker_data.get('profile_completeness', 0)
        if profile_quality < 20:
            risk_factors['profile_quality'] = 90
        elif profile_quality < 50:
            risk_factors['profile_quality'] = 60
        elif profile_quality < 80:
            risk_factors['profile_quality'] = 30
        else:
            risk_factors['profile_quality'] = 10
        
        # 4. 評価履歴リスク
        rating = worker_data.get('rating', 0)
        total_projects = worker_data.get('total_projects', 0)
        if total_projects == 0:
            risk_factors['rating_history'] = 100
        elif rating < 3.0:
            risk_factors['rating_history'] = 90
        elif rating < 4.0:
            risk_factors['rating_history'] = 50
        else:
            risk_factors['rating_history'] = 10
        
        # 5. 提出パターン異常
        risk_factors['submission_pattern'] = self.analyze_submission_pattern(
            worker_data.get('worker_name', ''), submission_data
        )
        
        # 6. デバイス指紋異常
        risk_factors['device_fingerprint'] = self.analyze_device_fingerprint(
            submission_data.get('device_fingerprint', '')
        )
        
        # 重み付き合計スコア計算
        total_score = sum(
            risk_factors[factor] * self.risk_weights[factor]
            for factor in risk_factors
        )
        
        # リスクレベル判定
        if total_score <= self.risk_thresholds['low']:
            risk_level = 'low'
        elif total_score <= self.risk_thresholds['medium']:
            risk_level = 'medium'
        elif total_score <= self.risk_thresholds['high']:
            risk_level = 'high'
        else:
            risk_level = 'critical'
        
        return {
            'total_score': round(total_score, 2),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendation': self.get_risk_recommendation(risk_level, total_score)
        }

    def analyze_submission_pattern(self, worker_name, submission_data):
        """
        提出パターンの異常を分析
        
        Args:
            worker_name (str): ワーカー名
            submission_data (dict): 提出データ
            
        Returns:
            int: パターン異常スコア (0-100)
        """
        risk_score = 0
        
        # 1. ワーカー名の怪しさチェック
        if self.is_suspicious_worker_name(worker_name):
            risk_score += 50
        
        # 2. 提出内容の短さ
        content = submission_data.get('content', '')
        if len(content) < 50:
            risk_score += 30
        
        # 3. 調査IDの形式チェック
        survey_ids = submission_data.get('extracted_ids', [])
        for survey_id in survey_ids:
            if self.is_suspicious_survey_id(survey_id):
                risk_score += 40
        
        # 4. 提出時間の異常（深夜や短時間での大量提出など）
        # これは実際のタイムスタンプデータが必要
        
        return min(risk_score, 100)

    def analyze_device_fingerprint(self, device_fingerprint):
        """
        デバイス指紋の異常を分析
        
        Args:
            device_fingerprint (str): デバイス指紋
            
        Returns:
            int: デバイス異常スコア (0-100)
        """
        if not device_fingerprint:
            return 50  # デバイス情報がない場合は中リスク
        
        # データベースから同じデバイス指紋の使用回数を確認
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT worker_count, associated_workers 
        FROM device_fingerprints 
        WHERE fingerprint_hash = ?
        ''', (device_fingerprint,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            # 新しいデバイス指紋
            return 20
        
        worker_count, associated_workers = result
        
        if worker_count > 5:
            return 90  # 5人以上が同じデバイスを使用している場合は高リスク
        elif worker_count > 2:
            return 60  # 3-5人の場合は中〜高リスク
        else:
            return 20  # 1-2人の場合は低リスク

    def is_suspicious_worker_name(self, worker_name):
        """
        ワーカー名の怪しさを判定
        
        Args:
            worker_name (str): ワーカー名
            
        Returns:
            bool: 怪しい場合True
        """
        suspicious_patterns = [
            r'^[a-z]{8,}$',           # 8文字以上の小文字のみ
            r'^[A-Z]{8,}$',           # 8文字以上の大文字のみ  
            r'^[a-zA-Z]{1,3}\d{5,}$', # 短い文字列＋長い数字
            r'^\w{10,}$',             # 10文字以上の英数字
            r'^user\d+$',             # user + 数字
            r'^test\d+$',             # test + 数字
            r'^temp\d+$',             # temp + 数字
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, worker_name, re.IGNORECASE):
                return True
        
        # 同じ文字の繰り返しチェック
        if len(set(worker_name.lower())) < 4 and len(worker_name) > 6:
            return True
        
        return False

    def is_suspicious_survey_id(self, survey_id):
        """
        調査IDの怪しさを判定
        
        Args:
            survey_id (str): 調査ID
            
        Returns:
            bool: 怪しい場合True
        """
        # 明らかに簡単すぎるID
        simple_patterns = [
            r'^1{8,}$',      # 1の繰り返し
            r'^0{8,}$',      # 0の繰り返し
            r'^123{5,}$',    # 123の繰り返し
            r'^\d{8}$',      # ちょうど8桁（短すぎる可能性）
        ]
        
        for pattern in simple_patterns:
            if re.match(pattern, survey_id):
                return True
        
        return False

    def check_duplicate_ids(self, submissions):
        """
        重複IDをチェックし、データベースに記録
        
        Args:
            submissions (list): 提出データのリスト
            
        Returns:
            dict: 重複分析結果
        """
        id_usage = defaultdict(list)
        
        # IDの使用状況を集計
        for submission in submissions:
            worker = submission['worker_name']
            for survey_id in submission.get('extracted_ids', []):
                id_usage[survey_id].append({
                    'worker': worker,
                    'submission_date': submission.get('submission_date', ''),
                    'content': submission.get('content', '')[:100]
                })
        
        # 重複IDをデータベースに記録
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        duplicates = {}
        for survey_id, usage_list in id_usage.items():
            if len(usage_list) > 1:
                duplicates[survey_id] = usage_list
                
                # データベースに記録
                workers_json = json.dumps([item['worker'] for item in usage_list])
                
                cursor.execute('''
                INSERT OR REPLACE INTO duplicate_ids 
                (survey_id, worker_count, associated_workers, risk_level)
                VALUES (?, ?, ?, ?)
                ''', (
                    survey_id, 
                    len(usage_list), 
                    workers_json,
                    'high' if len(usage_list) > 3 else 'medium'
                ))
        
        conn.commit()
        conn.close()
        
        return duplicates

    def check_device_duplicates(self, submissions):
        """
        デバイス重複をチェック
        
        Args:
            submissions (list): 提出データのリスト
            
        Returns:
            dict: デバイス重複分析結果
        """
        device_usage = defaultdict(list)
        
        for submission in submissions:
            device_fp = submission.get('device_fingerprint')
            if device_fp:
                device_usage[device_fp].append(submission['worker_name'])
        
        # データベースに記録
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        suspicious_devices = {}
        for device_fp, workers in device_usage.items():
            if len(workers) > 1:
                suspicious_devices[device_fp] = workers
                
                workers_json = json.dumps(list(set(workers)))
                
                cursor.execute('''
                INSERT OR REPLACE INTO device_fingerprints 
                (fingerprint_hash, worker_count, associated_workers, is_suspicious)
                VALUES (?, ?, ?, ?)
                ''', (
                    device_fp, 
                    len(set(workers)), 
                    workers_json,
                    len(set(workers)) > 2
                ))
        
        conn.commit()
        conn.close()
        
        return suspicious_devices

    def generate_screening_report(self, submissions, analysis_results):
        """
        スクリーニングレポートを生成
        
        Args:
            submissions (list): 提出データ
            analysis_results (dict): 分析結果
            
        Returns:
            str: レポート文字列
        """
        report = []
        report.append("=" * 70)
        report.append("高度スクリーニングシステム レポート")
        report.append("=" * 70)
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 第1段階: リスクスコア統計
        report.append("【第1段階: リスクスコア分析】")
        risk_levels = Counter()
        total_risk_score = 0
        high_risk_workers = []
        
        for submission in submissions:
            worker_risk = analysis_results.get('worker_risks', {}).get(submission['worker_name'], {})
            risk_level = worker_risk.get('risk_level', 'unknown')
            risk_score = worker_risk.get('total_score', 0)
            
            risk_levels[risk_level] += 1
            total_risk_score += risk_score
            
            if risk_level in ['high', 'critical']:
                high_risk_workers.append({
                    'worker': submission['worker_name'],
                    'risk_score': risk_score,
                    'risk_level': risk_level
                })
        
        report.append(f"総ワーカー数: {len(submissions)}")
        report.append(f"平均リスクスコア: {total_risk_score/len(submissions):.2f}")
        report.append(f"リスクレベル分布:")
        for level, count in risk_levels.items():
            percentage = count / len(submissions) * 100
            report.append(f"  - {level}: {count}名 ({percentage:.1f}%)")
        report.append("")
        
        # 高リスクワーカー詳細
        if high_risk_workers:
            report.append("【高リスクワーカー一覧】")
            for worker_info in sorted(high_risk_workers, key=lambda x: x['risk_score'], reverse=True):
                report.append(f"🚨 {worker_info['worker']} (スコア: {worker_info['risk_score']:.2f}, レベル: {worker_info['risk_level']})")
            report.append("")
        
        # 第2段階: 重複チェック結果
        report.append("【第2段階: 重複チェック結果】")
        
        # ID重複
        duplicate_ids = analysis_results.get('duplicate_ids', {})
        if duplicate_ids:
            report.append(f"重複ID検出数: {len(duplicate_ids)}")
            for survey_id, usage_list in duplicate_ids.items():
                report.append(f"🔄 ID: {survey_id} (使用者数: {len(usage_list)})")
                for usage in usage_list:
                    report.append(f"    - {usage['worker']} ({usage['submission_date']})")
            report.append("")
        else:
            report.append("✅ 重複IDは検出されませんでした")
            report.append("")
        
        # デバイス重複
        device_duplicates = analysis_results.get('device_duplicates', {})
        if device_duplicates:
            report.append(f"デバイス重複検出数: {len(device_duplicates)}")
            for device_fp, workers in device_duplicates.items():
                report.append(f"📱 デバイス: {device_fp[:16]}... (使用者数: {len(workers)})")
                for worker in workers:
                    report.append(f"    - {worker}")
            report.append("")
        else:
            report.append("✅ デバイス重複は検出されませんでした")
            report.append("")
        
        # 推奨アクション
        report.append("【推奨アクション】")
        critical_count = risk_levels.get('critical', 0)
        high_count = risk_levels.get('high', 0)
        
        if critical_count > 0:
            report.append(f"⚠️ 危険レベル {critical_count}名: 即座に非承認を検討")
        if high_count > 0:
            report.append(f"⚠️ 高リスクレベル {high_count}名: 詳細調査が必要")
        if duplicate_ids:
            report.append(f"⚠️ 重複ID {len(duplicate_ids)}件: 不正使用の可能性")
        if device_duplicates:
            report.append(f"⚠️ デバイス重複 {len(device_duplicates)}件: 複数アカウント使用の可能性")
        
        if not any([critical_count, high_count, duplicate_ids, device_duplicates]):
            report.append("✅ 特に問題となる要素は検出されませんでした")
        
        return "\n".join(report)

    def parse_account_age(self, date_text):
        """アカウント作成日をパースして日数を計算"""
        # 実装例（実際のフォーマットに応じて調整）
        try:
            # "2023年1月" 形式の場合
            if '年' in date_text and '月' in date_text:
                year = int(re.search(r'(\d{4})年', date_text).group(1))
                month = int(re.search(r'(\d{1,2})月', date_text).group(1))
                created_date = datetime(year, month, 1)
                return (datetime.now() - created_date).days
        except:
            pass
        return 0

    def parse_percentage(self, text):
        """パーセンテージをパース"""
        try:
            return float(re.search(r'(\d+(?:\.\d+)?)%', text).group(1))
        except:
            return 0

    def parse_number(self, text):
        """数値をパース"""
        try:
            return int(re.search(r'(\d+)', text).group(1))
        except:
            return 0

    def parse_rating(self, text):
        """評価をパース"""
        try:
            return float(re.search(r'(\d+(?:\.\d+)?)', text).group(1))
        except:
            return 0

    def estimate_profile_completeness(self, worker_element):
        """プロフィール充実度を推定"""
        score = 0
        
        # 各要素の存在をチェック
        if worker_element.find('img', class_='profile-image'):
            score += 20  # プロフィール画像
        if worker_element.find('div', class_='description'):
            score += 30  # 自己紹介
        if worker_element.find('span', class_='skills'):
            score += 25  # スキル情報
        if worker_element.find('span', class_='location'):
            score += 15  # 所在地
        if worker_element.find('span', class_='verification'):
            score += 10  # 認証情報
        
        return min(score, 100)

    def get_risk_recommendation(self, risk_level, score):
        """リスクレベルに応じた推奨アクションを取得"""
        recommendations = {
            'low': "✅ 承認可能 - 通常処理",
            'medium': "⚠️ 注意 - 内容を詳細確認後に判断",
            'high': "🔍 要調査 - 他の提出も含めて詳細調査が必要",
            'critical': "🚨 非承認推奨 - 不正の可能性が高い"
        }
        return recommendations.get(risk_level, "不明")

def main():
    parser = argparse.ArgumentParser(description='高度スクリーニングシステム')
    parser.add_argument('project_url', help='プロジェクトのURL')
    parser.add_argument('--max-pages', type=int, default=10, help='最大取得ページ数')
    parser.add_argument('--session-cookie', help='セッションクッキー')
    parser.add_argument('--output', help='レポート出力ファイル名')
    parser.add_argument('--db-path', help='スクリーニングデータベースのパス')
    
    args = parser.parse_args()
    
    # システムを初期化
    screening = AdvancedScreeningSystem(
        session_cookie=args.session_cookie,
        db_path=args.db_path
    )
    
    print("高度スクリーニングシステムを開始します...")
    print(f"対象URL: {args.project_url}")
    
    # 既存のスクレイピング機能を使用してデータを取得
    # （ここでは cw_duplicate_checker.py の機能を流用）
    from cw_duplicate_checker import CrowdWorksIDChecker
    
    id_checker = CrowdWorksIDChecker(session_cookie=args.session_cookie)
    submissions = id_checker.scrape_submission_data(args.project_url, args.max_pages)
    
    if not submissions:
        print("提出データが見つかりませんでした。")
        return
    
    print(f"取得した提出数: {len(submissions)}")
    
    # 第1段階: リスクスコア分析
    print("第1段階: リスクスコア分析を実行中...")
    worker_risks = {}
    
    for submission in submissions:
        worker_name = submission['worker_name']
        if worker_name not in worker_risks:
            # ワーカープロフィールデータの取得（実際の実装では適切に取得）
            worker_data = {
                'worker_name': worker_name,
                'account_age_days': 100,  # ダミーデータ
                'completion_rate': 80,
                'total_projects': 10,
                'rating': 4.2,
                'profile_completeness': 60
            }
            
            # デバイス指紋を生成（実際の実装ではJavaScriptから取得）
            device_fingerprint = hashlib.md5(
                f"{worker_name}_device".encode()
            ).hexdigest()
            
            submission['device_fingerprint'] = device_fingerprint
            
            risk_result = screening.calculate_risk_score(worker_data, submission)
            worker_risks[worker_name] = risk_result
    
    # 第2段階: 重複チェック
    print("第2段階: 重複チェックを実行中...")
    duplicate_ids = screening.check_duplicate_ids(submissions)
    device_duplicates = screening.check_device_duplicates(submissions)
    
    # 結果の集約
    analysis_results = {
        'worker_risks': worker_risks,
        'duplicate_ids': duplicate_ids,
        'device_duplicates': device_duplicates
    }
    
    # レポート生成
    output_file = args.output or f"screening_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = screening.generate_screening_report(submissions, analysis_results)
    
    # ファイル出力
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"スクリーニングレポートを {output_file} に保存しました。")
    print("\n" + report)
    
    # 危険レベルの警告
    critical_workers = [
        name for name, risk in worker_risks.items() 
        if risk.get('risk_level') == 'critical'
    ]
    
    if critical_workers:
        print(f"\n🚨 危険レベルのワーカーが {len(critical_workers)} 名検出されました！")
        print("即座に非承認を検討してください。")
    
    if duplicate_ids:
        print(f"\n🔄 重複IDが {len(duplicate_ids)} 件検出されました！")
    
    if device_duplicates:
        print(f"\n📱 デバイス重複が {len(device_duplicates)} 件検出されました！")

if __name__ == '__main__':
    main()
