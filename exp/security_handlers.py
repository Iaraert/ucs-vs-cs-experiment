"""
セキュリティログ処理エンドポイント
URLパラメータセキュリティ監視用
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
from utils.logger import ErrorLogger

security_bp = Blueprint('security', __name__)
error_logger = ErrorLogger()

# セキュリティログの保存ディレクトリ
SECURITY_LOG_DIR = os.path.join('logs', 'security')
os.makedirs(SECURITY_LOG_DIR, exist_ok=True)

@security_bp.route('/api/security/log', methods=['POST'])
def log_security_incident():
    """
    セキュリティインシデントをログに記録
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 必須フィールドの確認
        required_fields = ['type', 'timestamp']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # セキュリティログエントリを作成
        log_entry = {
            'timestamp': data['timestamp'],
            'type': data['type'],
            'details': data.get('details', {}),
            'user_agent': data.get('userAgent', ''),
            'url': data.get('url', ''),
            'ip_address': request.remote_addr,
            'headers': dict(request.headers)
        }
        
        # ログファイルに保存
        log_filename = f"security_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(SECURITY_LOG_DIR, log_filename)
        
        with open(log_filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
          # 重要度の高いインシデントは即座にアラート
        critical_types = [
            'invalid_parameter',
            'parameter_processing_error',
            'devtools_opened',
            'suspicious_activity'
        ]
        
        if data['type'] in critical_types:
            # 疑似例外を作成してログに記録
            try:
                raise ValueError(f"セキュリティインシデント: {data['type']}")
            except ValueError as se:
                error_logger.log_exception(se, level='WARNING', context=log_entry)
        
        return jsonify({'status': 'logged', 'timestamp': log_entry['timestamp']}), 200
        
    except Exception as e:
        error_logger.log_exception(e, context={'endpoint': 'security_log'})
        return jsonify({'error': 'Internal server error'}), 500

@security_bp.route('/api/security/status', methods=['GET'])
def get_security_status():
    """
    セキュリティ状態の取得
    """
    try:
        # 最近のセキュリティログを確認
        log_filename = f"security_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(SECURITY_LOG_DIR, log_filename)
        
        recent_incidents = []
        if os.path.exists(log_filepath):
            with open(log_filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 最新の10件を取得
                for line in lines[-10:]:
                    try:
                        incident = json.loads(line.strip())
                        # 個人情報を除去
                        sanitized_incident = {
                            'type': incident['type'],
                            'timestamp': incident['timestamp'],
                            'url': incident.get('url', '')
                        }
                        recent_incidents.append(sanitized_incident)
                    except json.JSONDecodeError:
                        continue
        
        return jsonify({
            'status': 'active',
            'recent_incidents': recent_incidents,
            'monitoring_active': True
        }), 200
        
    except Exception as e:
        error_logger.log_exception(e, context={'endpoint': 'security_status'})
        return jsonify({'error': 'Internal server error'}), 500

def analyze_security_patterns():
    """
    セキュリティパターンの分析
    """
    try:
        today = datetime.now().strftime('%Y%m%d')
        log_filename = f"security_{today}.log"
        log_filepath = os.path.join(SECURITY_LOG_DIR, log_filename)
        
        if not os.path.exists(log_filepath):
            return {'total_incidents': 0, 'patterns': {}}
        
        incident_types = {}
        ip_addresses = {}
        
        with open(log_filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    incident = json.loads(line.strip())
                    
                    # インシデントタイプの集計
                    incident_type = incident.get('type', 'unknown')
                    incident_types[incident_type] = incident_types.get(incident_type, 0) + 1
                    
                    # IPアドレスの集計
                    ip = incident.get('ip_address', 'unknown')
                    ip_addresses[ip] = ip_addresses.get(ip, 0) + 1
                    
                except json.JSONDecodeError:
                    continue
        
        # 疑わしいパターンの検出
        suspicious_patterns = []
        
        # 同一IPから多数のインシデント
        for ip, count in ip_addresses.items():
            if count > 10:  # 閾値
                suspicious_patterns.append({
                    'type': 'high_incident_ip',
                    'ip': ip,
                    'count': count
                })
        
        # 特定タイプのインシデントが多発
        for incident_type, count in incident_types.items():
            if count > 5 and incident_type in ['invalid_parameter', 'devtools_opened']:
                suspicious_patterns.append({
                    'type': 'high_incident_type',
                    'incident_type': incident_type,
                    'count': count
                })
        
        return {
            'total_incidents': sum(incident_types.values()),
            'incident_types': incident_types,
            'ip_distribution': ip_addresses,
            'suspicious_patterns': suspicious_patterns
        }
        
    except Exception as e:
        error_logger.log_exception(e, context={'function': 'analyze_security_patterns'})
        return {'error': 'Analysis failed'}
