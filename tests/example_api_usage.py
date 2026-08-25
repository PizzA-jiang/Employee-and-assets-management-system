#!/usr/bin/env python
"""
完整的 API 调用示例脚本
演示：登录 -> 增删改查员工/资产 -> 资产领用归还 -> 看板查看
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def print_response(name, resp):
    print(f"\n{'='*60}")
    print(f"{name}: {resp.status_code}")
    print(f"{'='*60}")
    try:
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    except:
        print(resp.text[:500])

def main():
    # 1. 登录获取 Token
    print("\n[LOCK] 步骤 1: 登录")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "testadmin",
        "password": "admin123"
    })
    print_response("登录", login_resp)
    
    if login_resp.status_code != 200:
        print("[FAIL] 登录失败，请检查用户名密码")
        return
    
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] 获取 Token 成功: {token[:30]}...")

    # 2. 获取当前用户信息
    print_response("获取当前用户", requests.get(f"{BASE_URL}/auth/me", headers=headers))

    # 3. 创建员工
    print("\n[USER] 步骤 2: 创建员工")
    emp_resp = requests.post(f"{BASE_URL}/employees", headers=headers, json={
        "user_id": 2,  # testemp 用户
        "employee_no": "EMP007",
        "name": "王五",
        "department": "测试部",
        "position": "自动化测试工程师",
        "phone": "13900139000",
        "hire_date": "2024-03-01T00:00:00"
    })
    print_response("创建员工", emp_resp)
    emp_id = emp_resp.json()["id"] if emp_resp.status_code == 201 else 2

    # 4. 查看员工列表
    print_response("员工列表", requests.get(f"{BASE_URL}/employees", headers=headers, params={"page": 1, "size": 10}))

    # 5. 创建资产
    print("\n[PC] 步骤 3: 创建资产")
    asset_resp = requests.post(f"{BASE_URL}/assets", headers=headers, json={
        "asset_no": "NB007",
        "name": "Dell XPS 15",
        "asset_type": "computer",
        "brand": "Dell",
        "model": "XPS 15 9530",
        "serial_number": "DL789012",
        "purchase_date": "2024-02-01T00:00:00",
        "purchase_price": 1300000,
        "location": "IT库房-A区",
        "remark": "高性能开发本"
    })
    print_response("创建资产", asset_resp)
    asset_id = asset_resp.json()["id"] if asset_resp.status_code == 201 else 1

    # 6. 查看资产列表和统计
    print_response("资产列表", requests.get(f"{BASE_URL}/assets", headers=headers))
    print_response("资产统计", requests.get(f"{BASE_URL}/assets/stats/summary", headers=headers))

    # 7. 资产领用
    print("\n[OUT] 步骤 4: 资产领用 (checkout)")
    checkout_resp = requests.post(f"{BASE_URL}/asset-logs", headers=headers, json={
        "asset_id": asset_id,
        "employee_id": emp_id,
        "action": "checkout",
        "remark": "自动化测试项目使用"
    })
    print_response("资产领用", checkout_resp)

    # 8. 查看资产状态 (应该变为 in_use)
    print_response("资产详情(领用后)", requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers))

    # 9. 查看流转记录
    print_response("资产流转历史", requests.get(f"{BASE_URL}/asset-logs/asset/{asset_id}", headers=headers))
    print_response("员工资产记录", requests.get(f"{BASE_URL}/asset-logs/employee/{emp_id}", headers=headers))

    # 10. 资产归还
    print("\n[IN] 步骤 5: 资产归还 (return)")
    return_resp = requests.post(f"{BASE_URL}/asset-logs", headers=headers, json={
        "asset_id": asset_id,
        "employee_id": emp_id,
        "action": "return",
        "remark": "项目结束归还"
    })
    print_response("资产归还", return_resp)

    # 11. 再次查看资产状态 (应该变为 available)
    print_response("资产详情(归还后)", requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers))

    # 12. 资产送修
    print("\n[REPAIR] 步骤 6: 资产送修 (maintenance_in)")
    maint_in = requests.post(f"{BASE_URL}/asset-logs", headers=headers, json={
        "asset_id": asset_id,
        "employee_id": emp_id,
        "action": "maintenance_in",
        "remark": "屏幕闪烁送修"
    })
    print_response("资产送修", maint_in)

    # 13. 修好领回
    print_response("资产修好", requests.post(f"{BASE_URL}/asset-logs", headers=headers, json={
        "asset_id": asset_id,
        "employee_id": emp_id,
        "action": "maintenance_out",
        "remark": "更换屏幕完成"
    }))

    # 14. 查看看板数据
    print("\n[CHART] 步骤 7: 数据看板")
    print_response("看板统计", requests.get(f"{BASE_URL}/dashboard/stats", headers=headers))
    print_response("按类型统计", requests.get(f"{BASE_URL}/dashboard/charts/assets-by-type", headers=headers))
    print_response("按状态统计", requests.get(f"{BASE_URL}/dashboard/charts/assets-by-status", headers=headers))
    print_response("按部门统计", requests.get(f"{BASE_URL}/dashboard/charts/employees-by-department", headers=headers))

    # 15. 导出 Excel
    print("\n[FILE] 步骤 8: 导出 Excel")
    export_assets = requests.get(f"{BASE_URL}/assets/export/excel", headers=headers)
    print_response("导出资产台账", export_assets)
    if export_assets.status_code == 200:
        with open("assets_export.xlsx", "wb") as f:
            f.write(export_assets.content)
        print("[OK] 已保存为 assets_export.xlsx")

    export_logs = requests.get(f"{BASE_URL}/asset-logs/export/excel", headers=headers)
    print_response("导出流转记录", export_logs)
    if export_logs.status_code == 200:
        with open("logs_export.xlsx", "wb") as f:
            f.write(export_logs.content)
        print("[OK] 已保存为 logs_export.xlsx")

    # 16. 清理测试数据
    print("\n[CLEAN] 步骤 9: 清理测试数据")
    print_response("删除资产", requests.delete(f"{BASE_URL}/assets/{asset_id}", headers=headers))
    print_response("删除员工", requests.delete(f"{BASE_URL}/employees/{emp_id}", headers=headers))

    print("\n" + "="*60)
    print("[OK] 所有示例执行完成！")
    print("="*60)

if __name__ == "__main__":
    # 先检查服务是否运行
    try:
        r = requests.get(f"{BASE_URL.replace('/api', '')}/health", timeout=3)
        if r.status_code != 200:
            print("[FAIL] 服务未运行，请先启动: py -m uvicorn app.main:app --reload")
            exit(1)
    except:
        print("[FAIL] 无法连接服务，请先启动: py -m uvicorn app.main:app --reload")
        exit(1)
    
    main()