# modules/capcut_api_client.py
import requests
import json
import os
import time
import shutil

from . import capcut_config

class CapcutAPIClient:
    def __init__(self, create_config, query_config, session=None, is_file_path=True):
        self.session = session if session else requests.Session()
        
        create_content = ""
        query_content = ""

        if is_file_path:
            print(f"CapcutAPIClient: Đang nạp cấu hình từ các file: {create_config}, {query_config}")
            if not os.path.exists(create_config):
                raise FileNotFoundError(f"File cấu hình không tồn tại: {create_config}")
            if not os.path.exists(query_config):
                raise FileNotFoundError(f"File cấu hình không tồn tại: {query_config}")
            with open(create_config, 'r', encoding='utf-8') as f:
                create_content = f.read()
            with open(query_config, 'r', encoding='utf-8') as f:
                query_content = f.read()
        else:
            print("CapcutAPIClient: Đang nạp cấu hình từ nội dung text trong bộ nhớ.")
            create_content = create_config
            query_content = query_config

        self.create_url, self.create_headers = self._parse_config_content(create_content, "Create")
        self.query_url, self.query_headers = self._parse_config_content(query_content, "Query")
        
        print("CapcutAPIClient initialized successfully.")

    def _parse_config_content(self, content, config_name=""):
        try:
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if not lines:
                raise ValueError(f"Nội dung cấu hình {config_name} trống.")

            url = lines[0]
            headers = {}
            for header_line in lines[1:]:
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    headers[key.strip()] = value.strip()
            return url, headers
        except Exception as e:
            print(f"LỖI (CapcutAPIClient): Lỗi khi phân tích nội dung cấu hình {config_name}: {e}")
            raise

    def create_tts_task(self, text, speaker_id, speaker_name_friendly):
        print(f"API_CLIENT: Creating TTS task for text: \"{text[:30]}...\", speaker: {speaker_id}")
        
        req_json_obj = {
            "speaker": speaker_id,
            "audio_config": {},
            "disable_caption": True
        }
        params_obj = {
            "text": text,
            "platform": 1
        }
        try:
            req_json_str = json.dumps(req_json_obj)
            params_str = json.dumps(params_obj)
        except Exception as e:
            print(f"API_CLIENT_ERROR (create_tts_task): Lỗi tạo chuỗi JSON: {e}")
            return None

        body = {
            "workspace_id": "7282401109132492802",
            "req_json": req_json_str,
            "smart_tool_type": 39,
            "params": params_str,
            "scene": 3
        }

        try:
            response = self.session.post(self.create_url, headers=self.create_headers, json=body, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            
            task_id = response_data.get("data", {}).get("task_id")
            if not task_id:
                 task_id = response_data.get("task_id")

            if task_id:
                print(f"API_CLIENT: Task created successfully. Task ID: {task_id}")
                return task_id
            else:
                print(f"API_CLIENT_ERROR (create_tts_task): Không tìm thấy task_id. Response: {str(response_data)[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"API_CLIENT_ERROR (create_tts_task - Request): {e}")
            return None
        except json.JSONDecodeError:
            print(f"API_CLIENT_ERROR (create_tts_task - JSON): Phản hồi không phải JSON. Content: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"API_CLIENT_ERROR (create_tts_task - Unknown): {e}")
            return None


    def query_tts_task(self, task_id):
        print(f"API_CLIENT: Querying task ID: {task_id}")

        body = {
            "task_id": task_id,
            "smart_tool_type": 39
        }

        try:
            response = self.session.post(self.query_url, headers=self.query_headers, json=body, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            print(f"API_CLIENT: Query response (raw): {str(response_data)[:200]}...")

            audio_url = None
            task_detail_list = response_data.get("data", {}).get("task_detail", [])
            if isinstance(task_detail_list, list):
                for detail in task_detail_list:
                    if isinstance(detail, dict) and detail.get("resource_type") == 32:
                        audio_url = detail.get("url")
                        if audio_url:
                            break
            
            task_info = response_data.get("data", {})
            task_status_str = task_info.get("status_str", "").upper()
            task_status_code = task_info.get("status")
            
            current_status = "UNKNOWN"
            if audio_url:
                current_status = "SUCCESS"
            elif task_status_str == "FAILED" or task_status_code == -1:
                current_status = "FAILED"
            elif task_status_str in ["PROCESSING", "PENDING", "QUEUEING"] or task_status_code in [0, 2]:
                current_status = "PROCESSING"
            elif task_status_str == "SUCCESS" or task_status_code == 1:
                current_status = "SUCCESS"

            return {'status': current_status, 'audio_url': audio_url, 'raw_response': response_data}

        except requests.exceptions.RequestException as e:
            print(f"API_CLIENT_ERROR (query_tts_task - Request): {e}")
            return {'status': 'REQUEST_ERROR', 'audio_url': None, 'raw_response': None}
        except json.JSONDecodeError:
            print(f"API_CLIENT_ERROR (query_tts_task - JSON): Phản hồi không phải JSON. Content: {response.text[:200]}")
            return {'status': 'JSON_ERROR', 'audio_url': None, 'raw_response': None}
        except Exception as e:
            print(f"API_CLIENT_ERROR (query_tts_task - Unknown): {e}")
            return {'status': 'UNKNOWN_ERROR', 'audio_url': None, 'raw_response': None}

    def poll_for_audio_url(self, task_id, max_retries=None, poll_interval_sec=None):
        max_r = max_retries if max_retries is not None else capcut_config.DEFAULT_MAX_POLL_RETRIES
        interval = poll_interval_sec if poll_interval_sec is not None else capcut_config.DEFAULT_POLL_INTERVAL_SEC
        
        print(f"API_CLIENT: Polling for task ID: {task_id} (retries={max_r}, interval={interval}s)")
        for attempt in range(max_r):
            print(f"API_CLIENT: Poll attempt {attempt + 1}/{max_r} for task {task_id}")
            result = self.query_tts_task(task_id)
            
            if result['status'] == "SUCCESS" and result['audio_url']:
                print(f"API_CLIENT: Polling successful. Audio URL: {result['audio_url']}")
                return result['audio_url']
            elif result['status'] == "FAILED" or \
                 result['status'] in ['CONFIG_ERROR', 'REQUEST_ERROR', 'JSON_ERROR', 'UNKNOWN_ERROR']:
                print(f"API_CLIENT: Polling failed for task {task_id}. Status: {result['status']}")
                return None
            
            if result['status'] == "SUCCESS" and not result['audio_url']:
                print(f"API_CLIENT: Polling task {task_id} reported SUCCESS but no audio_url. Assuming failure for polling.")
                return None

            if attempt < max_r - 1:
                print(f"API_CLIENT: Task {task_id} status: {result['status']}. Sleeping for {interval}s...")
                time.sleep(interval)
        
        print(f"API_CLIENT: Polling timed out for task ID: {task_id}")
        return None


    def download_audio(self, audio_url, output_filepath):
        print(f"API_CLIENT: Downloading audio from {audio_url} to {output_filepath}")
        try:
            response = self.session.get(audio_url, stream=True, timeout=60)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

            with open(output_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"API_CLIENT: Audio downloaded successfully to {output_filepath}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"API_CLIENT_ERROR (download_audio - Request): {e}")
            return False
        except Exception as e:
            print(f"API_CLIENT_ERROR (download_audio - Unknown): {e}")
            return False

    def get_audio_file(self, text, speaker_id, speaker_name_friendly, 
                       output_dir, filename_prefix="tts_", 
                       max_poll_retries=None, poll_interval_sec=None):

        print(f"API_CLIENT (get_audio_file): Processing text: \"{text[:30]}...\"")
        task_id = self.create_tts_task(text, speaker_id, speaker_name_friendly)
        if not task_id:
            print("API_CLIENT (get_audio_file): Failed to create task.")
            return None

        audio_url = self.poll_for_audio_url(task_id, max_poll_retries, poll_interval_sec)
        if not audio_url:
            print(f"API_CLIENT (get_audio_file): Failed to get audio URL for task {task_id}.")
            return None

        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time() * 1000)
        file_extension = os.path.splitext(audio_url.split('?')[0])[-1]
        if not file_extension or len(file_extension) > 5 :
            file_extension = ".mp3"

        output_filename = f"{filename_prefix}{timestamp}{file_extension}"
        output_filepath = os.path.join(output_dir, output_filename)

        if self.download_audio(audio_url, output_filepath):
            return output_filepath
        else:
            print(f"API_CLIENT (get_audio_file): Failed to download audio to {output_filepath}.")
            return None

    def close_session(self):
        if self.session:
            self.session.close()

            print("API_CLIENT: Requests session closed.")
