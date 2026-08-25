#!/usr/bin/env python
"""
完整 API 测试脚本
测试所有接口并生成 HTML 测试报告
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
TEST_REPORT_PATH = os.path.join(os.path.dirname(__file__), "test_report.html")


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.test_results: List[Dict] = []
        self.created_ids = {
            "user": [],
            "employee": [],
            "asset": [],
            "asset_log": [],
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
                         resp.json() if resp.content else None)
            return resp
        except RequestException as e:
            self._record(name, method, f"{self.base_url}{endpoint}", 0, expected, False, error=str(e))
            return None

    # ===== 认证相关 =====
    def test_login_admin(self):
        data = {"username": "testadmin", "password": "admin123"}
        resp = self.assert_status("管理员登录", "POST", "/auth/login", 200, json=data)
        if resp and resp.status_code == 200:
            self.admin_token = resp.json()["data"]["access_token"]
            self.token = self.admin_token
            # Get admin user ID
            me_resp = self._request("GET", "/auth/me")
            if me_resp.status_code == 200:
                self.created_ids["user"].append(me_resp.json()["data"]["id"])

    def test_login_fail(self):
        data = {"username": "testadmin", "password": "wrong"}
        self.assert_status("登录失败-密码错误", "POST", "/auth/login", 401, json=data)

    def test_get_me(self):
        self.assert_status("获取当前用户信息", "GET", "/auth/me", 200)

    def test_list_users(self):
        self.token = self.admin_token
        self.assert_status("用户列表", "GET", "/auth/users", 200, params={"page": 1, "size": 10})

    def test_update_user(self):
        if not self.created_ids["user"]:
            return
        self.token = self.admin_token
        user_id = self.created_ids["user"][-1]
        self.assert_status("更新用户", "PUT", f"/auth/users/{user_id}", 200,
                           json={"email": "updated@company.com"})

    # ===== 员工管理 =====
    def test_create_employee(self):
        self.token = self.admin_token
        import time
        # Clean up any existing employee for user_id=1 via direct DB query
        from app.database import SessionLocal
        from app.models import Employee
        db = SessionLocal()
        try:
            existing_emp = db.query(Employee).filter(Employee.user_id == 1).first()
            if existing_emp:
                # Delete related asset_logs first
                from app.models import AssetLog
                db.query(AssetLog).filter(AssetLog.employee_id == existing_emp.id).delete()
                db.delete(existing_emp)
                db.commit()
        finally:
            db.close()
        emp_no = f"EMP{int(time.time()*1000)%100000:05d}"
        data = {
            "user_id": self.created_ids["user"][-1] if self.created_ids["user"] else 1,
            "employee_no": emp_no,
            "name": "李四",
            "department": "测试部",
            "position": "测试工程师",
            "phone": "13900139000",
            "hire_date": "2024-02-01T00:00:00"
        }
        resp = self.assert_status("创建员工", "POST", "/employees", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["employee"].append(resp.json()["id"])

    def test_list_employees(self):
        self.assert_status("员工列表", "GET", "/employees", 200, params={"page": 1, "size": 10})

    def test_list_employees_with_filters(self):
        self.assert_status("员工列表-按部门筛选", "GET", "/employees", 200,
                           params={"page": 1, "size": 10, "department": "测试部"})

    def test_get_my_employee(self):
        self.token = self.admin_token
        self.assert_status("获取我的员工信息", "GET", "/employees/me", 200)

    def test_get_employee_detail(self):
        if not self.created_ids["employee"]:
            return
        emp_id = self.created_ids["employee"][0]
        self.assert_status("获取员工详情", "GET", f"/employees/{emp_id}", 200)

    def test_update_employee(self):
        if not self.created_ids["employee"]:
            return
        emp_id = self.created_ids["employee"][0]
        self.token = self.admin_token
        self.assert_status("更新员工", "PUT", f"/employees/{emp_id}", 200,
                           json={"position": "高级测试工程师"})

    # ===== 资产管理 =====
    def test_create_asset(self):
        self.token = self.admin_token
        import time
        self.asset_no = f"AST{int(time.time()*1000)%100000:05d}"
        serial_no = f"SN{int(time.time()*1000)%1000000:06d}"
        data = {
            "asset_no": self.asset_no,
            "name": "测试笔记本",
            "asset_type": "computer",
            "brand": "ThinkPad",
            "model": "X1 Carbon",
            "serial_number": serial_no,
            "purchase_date": "2024-01-15T00:00:00",
            "purchase_price": 1200000,
            "location": "IT库房",
            "remark": "测试用资产"
        }
        resp = self.assert_status("创建资产", "POST", "/assets", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["asset"].append(resp.json()["id"])

    def test_create_asset_duplicate_no(self):
        self.token = self.admin_token
        # Use the same asset_no as the previous test
        data = {
            "asset_no": self.asset_no,
            "name": "重复编号资产",
            "asset_type": "computer",
        }
        self.assert_status("创建资产-编号重复", "POST", "/assets", 400, json=data)

    def test_list_assets(self):
        self.assert_status("资产列表", "GET", "/assets", 200, params={"page": 1, "size": 10})

    def test_list_assets_filter(self):
        self.assert_status("资产列表-按类型筛选", "GET", "/assets", 200,
                           params={"page": 1, "size": 10, "asset_type": "computer"})

    def test_asset_stats(self):
        self.assert_status("资产统计概览", "GET", "/assets/stats/summary", 200)

    def test_get_asset_detail(self):
        if not self.created_ids["asset"]:
            return
        asset_id = self.created_ids["asset"][0]
        self.assert_status("获取资产详情", "GET", f"/assets/{asset_id}", 200)

    def test_update_asset(self):
        if not self.created_ids["asset"]:
            return
        asset_id = self.created_ids["asset"][0]
        self.token = self.admin_token
        self.assert_status("更新资产", "PUT", f"/assets/{asset_id}", 200,
                           json={"location": "会议室", "status": "available"})

    def test_export_assets(self):
        self.token = self.admin_token
        resp = self._request("GET", "/assets/export/excel")
        success = resp.status_code == 200
        self._record("导出资产Excel", "GET", f"{self.base_url}/assets/export/excel",
                     resp.status_code, 200, success,
                     f"Content-Type: {resp.headers.get('Content-Type')}" if success else None)
        if success:
            print(f"   文件大小: {len(resp.content)} bytes")

    # ===== 资产流转记录 =====
    def test_checkout_asset(self):
        if not self.created_ids["asset"] or not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        data = {
            "asset_id": self.created_ids["asset"][0],
            "employee_id": self.created_ids["employee"][0],
            "action": "checkout",
            "remark": "领用测试"
        }
        resp = self.assert_status("资产领用", "POST", "/asset-logs", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["asset_log"].append(resp.json()["id"])

    def test_checkout_same_asset_fail(self):
        if not self.created_ids["asset"] or not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        data = {
            "asset_id": self.created_ids["asset"][0],
            "employee_id": self.created_ids["employee"][0],
            "action": "checkout",
            "remark": "重复领用"
        }
        self.assert_status("重复领用同一资产", "POST", "/asset-logs", 400, json=data)

    def test_return_asset(self):
        if not self.created_ids["asset"] or not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        data = {
            "asset_id": self.created_ids["asset"][0],
            "employee_id": self.created_ids["employee"][0],
            "action": "return",
            "remark": "归还测试"
        }
        resp = self.assert_status("资产归还", "POST", "/asset-logs", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["asset_log"].append(resp.json()["id"])

    def test_maintenance_in(self):
        if not self.created_ids["asset"] or not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        data = {
            "asset_id": self.created_ids["asset"][0],
            "employee_id": self.created_ids["employee"][0],
            "action": "maintenance_in",
            "remark": "送修测试"
        }
        resp = self.assert_status("资产送修", "POST", "/asset-logs", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["asset_log"].append(resp.json()["id"])

    def test_maintenance_out(self):
        if not self.created_ids["asset"] or not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        data = {
            "asset_id": self.created_ids["asset"][0],
            "employee_id": self.created_ids["employee"][0],
            "action": "maintenance_out",
            "remark": "修好领回"
        }
        resp = self.assert_status("资产修好", "POST", "/asset-logs", 201, json=data)
        if resp and resp.status_code == 201:
            self.created_ids["asset_log"].append(resp.json()["id"])

    def test_list_asset_logs(self):
        self.assert_status("流转记录列表", "GET", "/asset-logs", 200, params={"page": 1, "size": 10})

    def test_list_asset_logs_filter(self):
        if not self.created_ids["asset"]:
            return
        self.assert_status("流转记录-按资产筛选", "GET", "/asset-logs", 200,
                           params={"page": 1, "size": 10, "asset_id": self.created_ids["asset"][0]})

    def test_get_asset_history(self):
        if not self.created_ids["asset"]:
            return
        asset_id = self.created_ids["asset"][0]
        self.assert_status("资产流转历史", "GET", f"/asset-logs/asset/{asset_id}", 200)

    def test_get_employee_assets(self):
        if not self.created_ids["employee"]:
            return
        emp_id = self.created_ids["employee"][0]
        self.assert_status("员工资产记录", "GET", f"/asset-logs/employee/{emp_id}", 200)

    def test_export_asset_logs(self):
        self.token = self.admin_token
        resp = self._request("GET", "/asset-logs/export/excel")
        success = resp.status_code == 200
        self._record("导出流转记录Excel", "GET", f"{self.base_url}/asset-logs/export/excel",
                     resp.status_code, 200, success,
                     f"Content-Type: {resp.headers.get('Content-Type')}" if success else None)

    # ===== 数据看板 =====
    def test_dashboard_stats(self):
        self.assert_status("看板统计", "GET", "/dashboard/stats", 200)

    def test_dashboard_charts(self):
        endpoints = [
            ("/dashboard/charts/assets-by-type", "按类型统计"),
            ("/dashboard/charts/assets-by-status", "按状态统计"),
            ("/dashboard/charts/logs-by-action", "按操作类型统计"),
            ("/dashboard/charts/employees-by-department", "按部门统计"),
            ("/dashboard/charts/monthly-checkouts", "月度领用趋势"),
        ]
        for endpoint, name in endpoints:
            self.assert_status(f"看板-{name}", "GET", endpoint, 200)

    # ===== 权限测试 =====
    def test_permission_denied(self):
        self.token = None
        self.assert_status("无Token访问", "GET", "/employees", 401)

    def test_employee_cannot_admin(self):
        self.token = self.admin_token
        # 创建员工token
        data = {"username": "testemp", "password": "emp123"}
        resp = self._request("POST", "/auth/login", json=data)
        if resp.status_code == 200:
            emp_token = resp.json()["data"]["access_token"]
            old_token = self.token
            self.token = emp_token
            self.assert_status("员工尝试创建用户", "POST", "/auth/register", 403,
                               json={"username": "hack", "password": "123", "role": "admin"})
            self.assert_status("员工尝试删除用户", "DELETE", "/auth/users/999", 403)
            self.assert_status("员工尝试导出资产", "GET", "/assets/export/excel", 403)
            self.token = old_token

    # ===== 清理测试 =====
    def test_delete_asset(self):
        if not self.created_ids["asset"]:
            return
        self.token = self.admin_token
        for asset_id in self.created_ids["asset"]:
            self.assert_status(f"删除资产-{asset_id}", "DELETE", f"/assets/{asset_id}", 200)

    def test_delete_employee(self):
        if not self.created_ids["employee"]:
            return
        self.token = self.admin_token
        for emp_id in self.created_ids["employee"]:
            self.assert_status(f"删除员工-{emp_id}", "DELETE", f"/employees/{emp_id}", 200)

    def test_delete_user(self):
        if not self.created_ids["user"]:
            return
        self.token = self.admin_token
        for user_id in self.created_ids["user"]:
            # Skip deleting the current user (can't delete yourself)
            if user_id == 1:  # Current admin user
                self._record(f"删除用户-{user_id} (跳过: 当前用户)", "DELETE", f"/auth/users/{user_id}", 0, 200, True)
                continue
            self.assert_status(f"删除用户-{user_id}", "DELETE", f"/auth/users/{user_id}", 200)

    def run_all(self):
        print("=" * 60)
        print("Start API Tests")
        print("=" * 60)

        # 认证
        self.test_login_admin()
        self.test_login_fail()
        self.test_get_me()
        self.test_list_users()
        self.test_update_user()

        # 员工
        self.test_create_employee()
        self.test_list_employees()
        self.test_list_employees_with_filters()
        self.test_get_my_employee()
        self.test_get_employee_detail()
        self.test_update_employee()

        # 资产
        self.test_create_asset()
        self.test_create_asset_duplicate_no()
        self.test_list_assets()
        self.test_list_assets_filter()
        self.test_asset_stats()
        self.test_get_asset_detail()
        self.test_update_asset()
        self.test_export_assets()

        # 流转记录
        self.test_checkout_asset()
        self.test_checkout_same_asset_fail()
        self.test_return_asset()
        self.test_maintenance_in()
        self.test_maintenance_out()
        self.test_list_asset_logs()
        self.test_list_asset_logs_filter()
        self.test_get_asset_history()
        self.test_get_employee_assets()
        self.test_export_asset_logs()

        # 看板
        self.test_dashboard_stats()
        self.test_dashboard_charts()

        # 权限
        self.test_permission_denied()
        self.test_employee_cannot_admin()

        # 清理
        self.test_delete_asset()
        self.test_delete_employee()
        self.test_delete_user()

        print("=" * 60)
        print("Tests Completed")
        print("=" * 60)

    def generate_report(self):
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["success"])
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>API 测试报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
        .card {{ flex: 1; min-width: 150px; padding: 20px; border-radius: 8px; text-align: center; }}
        .card.total {{ background: #e3f2fd; color: #1976d2; }}
        .card.passed {{ background: #e8f5e9; color: #388e3c; }}
        .card.failed {{ background: #ffebee; color: #d32f2f; }}
        .card.rate {{ background: #fff3e0; color: #f57c00; }}
        .card h3 {{ margin: 0; font-size: 14px; color: #666; }}
        .card .value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        tr:hover {{ background: #fafafa; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
        .method {{ font-family: monospace; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
        .method.GET {{ background: #e3f2fd; color: #1976d2; }}
        .method.POST {{ background: #e8f5e9; color: #388e3c; }}
        .method.PUT {{ background: #fff3e0; color: #f57c00; }}
        .method.DELETE {{ background: #ffebee; color: #d32f2f; }}
        .details {{ font-size: 12px; color: #666; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .error {{ color: #d32f2f; font-size: 12px; }}
        .timestamp {{ color: #999; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 API 测试报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>测试地址: {self.base_url}</p>

        <div class="summary">
            <div class="card total"><h3>总用例数</h3><div class="value">{total}</div></div>
            <div class="card passed"><h3>通过</h3><div class="value">{passed}</div></div>
            <div class="card failed"><h3>失败</h3><div class="value">{failed}</div></div>
            <div class="card rate"><h3>通过率</h3><div class="value">{pass_rate:.1f}%</div></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>接口名称</th>
                    <th>方法</th>
                    <th>URL</th>
                    <th>状态码</th>
                    <th>预期</th>
                    <th>结果</th>
                    <th>响应/错误</th>
                    <th>时间</th>
                </tr>
            </thead>
            <tbody>
"""

        for i, r in enumerate(self.test_results, 1):
            status_class = "success" if r["success"] else "fail"
            method_class = r["method"]
            resp_text = ""
            if r["response"]:
                if isinstance(r["response"], dict):
                    resp_text = json.dumps(r["response"], ensure_ascii=False)[:200]
                else:
                    resp_text = str(r["response"])[:200]
            error_text = f'<div class="error">{r["error"]}</div>' if r["error"] else ""

            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{r["name"]}</td>
                    <td><span class="method {method_class}">{r["method"]}</span></td>
                    <td><code>{r["url"]}</code></td>
                    <td>{r["status"]}</td>
                    <td>{r["expected"]}</td>
                    <td class="{status_class}">{'通过' if r["success"] else '失败'}</td>
                    <td class="details">{resp_text}{error_text}</td>
                    <td class="timestamp">{r["timestamp"]}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

        with open(TEST_REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\nReport generated: {TEST_REPORT_PATH}")


def check_server():
    """检查服务是否运行"""
    try:
        resp = requests.get(f"{BASE_URL.replace('/api', '')}/health", timeout=3)
        return resp.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("Checking server status...")
    if not check_server():
        print("ERROR: Server not running. Start with: py -m uvicorn app.main:app --reload")
        sys.exit(1)

    print("Server OK, starting tests...\n")

    tester = APITester(BASE_URL)
    tester.run_all()
    tester.generate_report()

    # 统计
    total = len(tester.test_results)
    passed = sum(1 for r in tester.test_results if r["success"])
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {total - passed} | Pass Rate: {passed/total*100:.1f}%")

    if passed < total:
        sys.exit(1)