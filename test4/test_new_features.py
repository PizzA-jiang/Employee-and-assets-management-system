#!/usr/bin/env python
"""
新功能测试脚本
测试人员Excel导出、关键词检索、操作日志、云盘功能
"""
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from requests.exceptions import RequestException


BASE_URL = "http://localhost:8000/api"


class NewFeatureTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.emp_token = None
        self.test_results: List[Dict] = []
        self.created_ids = {
            "employee": [],
            "asset": [],
            "cloud_file": [],
        }

    def _record(self, name: str, method: str, url: str, status: int, expected: int,
                success: bool, response: Any = None, error: str = None):
        self.test_results.append({
            "name": name,
            "method": method,
            "url": url,
            "status": status,
            "expected": expected,
            "success": success,
            "response": response,
            "error": error,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        })
        icon = "PASS" if success else "FAIL"
        print(f"{icon} {method} {url} -> {status} (expected {expected})")
        if error:
            print(f"   Error: {error}")

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.token}"
        return requests.request(method, url, headers=headers, timeout=10, **kwargs)

    def assert_status(self, name: str, method: str, endpoint: str, expected: int = 200, **kwargs) -> requests.Response:
        try:
            resp = self._request(method, endpoint, **kwargs)
            success = resp.status_code == expected
            self._record(name, method, f"{self.base_url}{endpoint}", resp.status_code, expected, success,
                         resp.json() if resp.content and 'json' in resp.headers.get('content-type', '') else None)
            return resp
        except RequestException as e:
            self._record(name, method, f"{self.base_url}{endpoint}", 0, expected, False, error=str(e))
            return None

    # ===== 登录 =====
    def test_login_admin(self):
        data = {"username": "root", "password": "101704"}
        resp = self.assert_status("管理员登录", "POST", "/auth/login", 200, json=data)
        if resp and resp.status_code == 200:
            self.admin_token = resp.json()["data"]["access_token"]
            self.token = self.admin_token

    def test_login_employee(self):
        data = {"username": "testemp", "password": "emp123"}
        resp = self.assert_status("员工登录", "POST", "/auth/login", 200, json=data)
        if resp and resp.status_code == 200:
            self.emp_token = resp.json()["data"]["access_token"]

    # ===== 人员Excel导出 =====
    def test_export_employees_admin(self):
        self.token = self.admin_token
        resp = self._request("GET", "/employees/export/excel")
        success = resp.status_code == 200 and 'spreadsheet' in resp.headers.get('content-type', '')
        self._record("管理员导出员工Excel", "GET", f"{self.base_url}/employees/export/excel",
                     resp.status_code, 200, success,
                     f"Content-Type: {resp.headers.get('content-type')}, Size: {len(resp.content)} bytes" if success else None)

    def test_export_employees_employee(self):
        self.token = self.emp_token
        self.assert_status("员工导出员工Excel(拒绝)", "GET", "/employees/export/excel", 403)

    # ===== 关键词检索-员工 =====
    def test_employees_keyword_name(self):
        self.token = self.admin_token
        self.assert_status("员工-按姓名搜索", "GET", "/employees", 200,
                           params={"keyword": "test", "page": 1, "size": 10})

    def test_employees_keyword_department(self):
        self.token = self.admin_token
        self.assert_status("员工-按部门搜索", "GET", "/employees", 200,
                           params={"keyword": "测试", "page": 1, "size": 10})

    def test_employees_keyword_no_match(self):
        self.token = self.admin_token
        resp = self.assert_status("员工-无匹配结果", "GET", "/employees", 200,
                                  params={"keyword": "XYZ999NONEXIST", "page": 1, "size": 10})
        if resp and resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("items", []) == []:
                print("   Verified: items is empty as expected")

    # ===== 关键词检索-资产 =====
    def test_assets_keyword_name(self):
        self.token = self.admin_token
        self.assert_status("资产-按名称搜索", "GET", "/assets", 200,
                           params={"keyword": "电脑", "page": 1, "size": 10})

    def test_assets_keyword_brand(self):
        self.token = self.admin_token
        self.assert_status("资产-按品牌搜索", "GET", "/assets", 200,
                           params={"keyword": "Dell", "page": 1, "size": 10})

    def test_assets_keyword_no_match(self):
        self.token = self.admin_token
        resp = self.assert_status("资产-无匹配结果", "GET", "/assets", 200,
                                  params={"keyword": "XYZ999NONEXIST", "page": 1, "size": 10})
        if resp and resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("items", []) == []:
                print("   Verified: items is empty as expected")

    # ===== 操作日志 =====
    def test_operation_logs_list(self):
        self.token = self.admin_token
        self.assert_status("查询操作日志", "GET", "/operation-logs", 200,
                           params={"page": 1, "size": 10})

    def test_operation_logs_filter_type(self):
        self.token = self.admin_token
        self.assert_status("操作日志-按类型筛选", "GET", "/operation-logs", 200,
                           params={"target_type": "asset", "page": 1, "size": 10})

    def test_operation_logs_filter_date(self):
        self.token = self.admin_token
        self.assert_status("操作日志-按时间筛选", "GET", "/operation-logs", 200,
                           params={"start_date": "2024-01-01T00:00:00", "page": 1, "size": 10})

    def test_operation_logs_employee_denied(self):
        self.token = self.emp_token
        self.assert_status("员工访问操作日志(拒绝)", "GET", "/operation-logs", 403)

    # ===== 云盘功能 =====
    def test_cloud_files_upload(self):
        self.token = self.admin_token
        test_content = b"Test file content for cloud storage"
        files = {"file": ("test_upload.txt", test_content, "text/plain")}
        resp = self.assert_status("上传文件", "POST", "/cloud-files/upload", 200, files=files)
        if resp and resp.status_code == 200:
            data = resp.json()
            file_id = data.get("id")
            if file_id:
                self.created_ids["cloud_file"].append(file_id)

    def test_cloud_files_upload_invalid_type(self):
        self.token = self.admin_token
        test_content = b"Invalid file content"
        files = {"file": ("test.exe", test_content, "application/octet-stream")}
        self.assert_status("上传不支持的文件类型", "POST", "/cloud-files/upload", 400, files=files)

    def test_cloud_files_list(self):
        self.token = self.admin_token
        self.assert_status("查看文件列表", "GET", "/cloud-files", 200,
                           params={"page": 1, "size": 10})

    def test_cloud_files_keyword_search(self):
        self.token = self.admin_token
        self.assert_status("云盘-关键词搜索", "GET", "/cloud-files", 200,
                           params={"keyword": "test", "page": 1, "size": 10})

    def test_cloud_files_download(self):
        self.token = self.admin_token
        if not self.created_ids["cloud_file"]:
            print("SKIP: No cloud file to download")
            return
        file_id = self.created_ids["cloud_file"][0]
        resp = self._request("GET", f"/cloud-files/{file_id}/download")
        success = resp.status_code == 200
        self._record("下载文件", "GET", f"{self.base_url}/cloud-files/{file_id}/download",
                     resp.status_code, 200, success,
                     f"Size: {len(resp.content)} bytes" if success else None)

    def test_cloud_files_delete(self):
        self.token = self.admin_token
        if not self.created_ids["cloud_file"]:
            print("SKIP: No cloud file to delete")
            return
        file_id = self.created_ids["cloud_file"].pop(0)
        self.assert_status("删除文件", "DELETE", f"/cloud-files/{file_id}", 200)

    def test_cloud_files_share(self):
        self.token = self.admin_token
        if not self.created_ids["cloud_file"]:
            print("SKIP: No cloud file to share")
            return
        file_id = self.created_ids["cloud_file"][0]
        users_resp = self._request("GET", "/auth/users", params={"page": 1, "size": 10})
        target_user_id = None
        if users_resp.status_code == 200:
            users_data = users_resp.json()
            items = users_data.get("data", []) if isinstance(users_data.get("data"), list) else users_data.get("data", {}).get("items", [])
            for u in items:
                if u.get("role") == "employee":
                    target_user_id = u["id"]
                    break
            if not target_user_id and items:
                target_user_id = items[0]["id"]
        if not target_user_id:
            print("SKIP: No target user to share with")
            return
        data = {"user_ids": [target_user_id]}
        self.assert_status("管理员共享文件", "POST", f"/cloud-files/{file_id}/share", 200, json=data)

    def test_cloud_files_shared_list(self):
        self.token = self.emp_token
        self.assert_status("查看共享文件列表", "GET", "/cloud-files/shared", 200,
                           params={"page": 1, "size": 10})

    # ===== 运行所有测试 =====
    def run_all(self):
        print("=" * 60)
        print("Start New Feature Tests")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 登录
        self.test_login_admin()
        self.test_login_employee()

        # 人员Excel导出
        print("\n--- 人员Excel导出 ---")
        self.test_export_employees_admin()
        self.test_export_employees_employee()

        # 关键词检索-员工
        print("\n--- 关键词检索-员工 ---")
        self.test_employees_keyword_name()
        self.test_employees_keyword_department()
        self.test_employees_keyword_no_match()

        # 关键词检索-资产
        print("\n--- 关键词检索-资产 ---")
        self.test_assets_keyword_name()
        self.test_assets_keyword_brand()
        self.test_assets_keyword_no_match()

        # 操作日志
        print("\n--- 操作日志 ---")
        self.test_operation_logs_list()
        self.test_operation_logs_filter_type()
        self.test_operation_logs_filter_date()
        self.test_operation_logs_employee_denied()

        # 云盘功能
        print("\n--- 云盘功能 ---")
        self.test_cloud_files_upload()
        self.test_cloud_files_upload_invalid_type()
        self.test_cloud_files_list()
        self.test_cloud_files_keyword_search()
        self.test_cloud_files_download()
        self.test_cloud_files_share()
        self.test_cloud_files_shared_list()
        self.test_cloud_files_delete()

        print("\n" + "=" * 60)
        print("Tests Completed")
        print("=" * 60)

    def print_summary(self):
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Pass Rate: {pass_rate:.1f}%")

        if failed > 0:
            print("\nFailed tests:")
            for r in self.test_results:
                if not r["success"]:
                    print(f"  - {r['name']}: {r['method']} {r['url']} -> {r['status']} (expected {r['expected']})")


def check_server():
    try:
        resp = requests.get("http://localhost:8000/health", timeout=3)
        return resp.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("Checking server status...")
    if not check_server():
        print("ERROR: Server not running. Start with: start.bat or uvicorn app.main:app")
        sys.exit(1)

    print("Server OK, starting tests...\n")

    tester = NewFeatureTester(BASE_URL)
    tester.run_all()
    tester.print_summary()

    total = len(tester.test_results)
    passed = sum(1 for r in tester.test_results if r["success"])
    if passed < total:
        sys.exit(1)
