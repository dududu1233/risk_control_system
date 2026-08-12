"""风控中台种子数据：权限、角色、用户、示例策略。可重复执行（幂等）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.models import (
    BlacklistEntry, InspectionRecord, Permission, ProductionBatch, RiskPolicy,
    Role, RolePermission, User, UserRole,
)

PERMISSIONS = [
    ("risk:policy:view", "策略查看"),
    ("risk:policy:manage", "策略管理"),
    ("risk:event:view", "事件查看"),
    ("risk:event:evaluate", "风险决策"),
    ("risk:blacklist:view", "黑白名单查看"),
    ("risk:blacklist:manage", "黑白名单管理"),
    ("dashboard:view", "看板查看"),
    ("audit:view", "审计查看"),
    ("quality:view", "生产质量查看"),
    ("quality:manage", "生产质量管理"),
]

ROLES = {
    "super_admin": [c for c, _ in PERMISSIONS],
    "risk_admin": [
        "risk:policy:view", "risk:policy:manage", "risk:event:view",
        "risk:event:evaluate", "risk:blacklist:view", "risk:blacklist:manage",
        "dashboard:view", "quality:view", "quality:manage",
    ],
    "auditor": ["risk:event:view", "dashboard:view", "audit:view", "quality:view"],
    "user": ["dashboard:view", "quality:view"],
    "quality_inspector": ["quality:view", "quality:manage"],
}

USERS = [
    ("admin", "123456", "超级管理员", True, "super_admin"),
    ("risk_admin", "123456", "风控管理员", False, "risk_admin"),
    ("auditor", "123456", "审计员", False, "auditor"),
    ("normal_user", "123456", "普通用户", False, "user"),
    ("qc_inspector", "123456", "质检员", False, "quality_inspector"),
]

DEMO_POLICIES = [
    RiskPolicy(
        name="高频知识导出阻断", description="单次导出数量超过 100 直接阻断",
        event_type="EXPORT", enabled=True, priority=10, action="BLOCK", risk_score=100,
        conditions=[{"field": "export_count", "op": "gt", "value": 100}],
    ),
    RiskPolicy(
        name="失败登录次数过多", description="失败登录次数 >= 5 直接阻断并拉黑 IP",
        event_type="LOGIN", enabled=True, priority=20, action="ADD_BLACKLIST", risk_score=90,
        conditions=[{"field": "failed_attempts", "op": "gte", "value": 5}],
    ),
    RiskPolicy(
        name="非工作时间大量访问预警", description="凌晨且访问量过大触发预警",
        event_type="KNOWLEDGE_ACCESS", enabled=True, priority=50, action="WARN", risk_score=60,
        conditions=[{"field": "hour", "op": "lt", "value": 8}, {"field": "count", "op": "gt", "value": 50}],
    ),
    RiskPolicy(
        name="敏感部门访问预警", description="访问涉密部门知识触发预警",
        event_type="KNOWLEDGE_ACCESS", enabled=True, priority=60, action="WARN", risk_score=40,
        conditions=[{"field": "department", "op": "eq", "value": "涉密"}],
    ),
    RiskPolicy(
        name="敏感词命中预警", description="查询中包含「密码」「涉密」等敏感词预警",
        event_type="KNOWLEDGE_ACCESS", enabled=True, priority=70, action="WARN", risk_score=30,
        conditions=[{"field": "query", "op": "contains", "value": "密码"}],
    ),
    # ---- 生产质量风控策略 ----
    RiskPolicy(
        name="生产质量-不合格率超阈值阻断", description="批次不合格率 > 5% 直接阻断，禁止流入下道工序",
        event_type="PRODUCTION_INSPECTION", enabled=True, priority=10, action="BLOCK", risk_score=100,
        conditions=[{"field": "defect_rate", "op": "gt", "value": 5}],
    ),
    RiskPolicy(
        name="生产质量-抽检不合格预警", description="抽检发现不合格项，触发预警并建议复检/降级",
        event_type="PRODUCTION_INSPECTION", enabled=True, priority=30, action="WARN", risk_score=50,
        conditions=[{"field": "failed_qty", "op": "gt", "value": 0}, {"field": "inspected_qty", "op": "gt", "value": 0}],
    ),
    RiskPolicy(
        name="生产质量-整批漏检告警", description="批次未做质检就流转(漏检)触发告警",
        event_type="PRODUCTION_INSPECTION", enabled=True, priority=40, action="ALERT", risk_score=40,
        conditions=[{"field": "is_leak", "op": "eq", "value": True}],
    ),
    RiskPolicy(
        name="生产质量-产线连续不合格阻断", description="同一产线连续 >= 3 批不合格，疑似系统性问题，阻断并建议停线排查",
        event_type="PRODUCTION_INSPECTION", enabled=True, priority=20, action="BLOCK", risk_score=100,
        conditions=[{"field": "consecutive_failed", "op": "gte", "value": 3}],
    ),
]


def main():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    perm_map = {}
    for code, name in PERMISSIONS:
        p = db.query(Permission).filter(Permission.code == code).first()
        if not p:
            p = Permission(code=code, name=name)
            db.add(p)
            db.commit()
        perm_map[code] = p

    role_map = {}
    for rname, perms in ROLES.items():
        r = db.query(Role).filter(Role.name == rname).first()
        if not r:
            r = Role(name=rname, description=rname, is_system=True)
            db.add(r)
            db.commit()
        role_map[rname] = r
        for code in perms:
            rp = db.query(RolePermission).filter(
                RolePermission.role_id == r.id, RolePermission.permission_code == code
            ).first()
            if not rp:
                db.add(RolePermission(role_id=r.id, permission_code=code))
        db.commit()

    for uname, pw, disp, is_sa, rname in USERS:
        u = db.query(User).filter(User.username == uname).first()
        if not u:
            u = User(
                username=uname, display_name=disp, password_hash=hash_password(pw),
                is_superadmin=is_sa, status="ENABLED",
            )
            db.add(u)
            db.commit()
        ur = db.query(UserRole).filter(
            UserRole.user_id == u.id, UserRole.role_id == role_map[rname].id
        ).first()
        if not ur:
            db.add(UserRole(user_id=u.id, role_id=role_map[rname].id))
            db.commit()

    added = 0
    for p in DEMO_POLICIES:
        exists = db.query(RiskPolicy).filter(RiskPolicy.name == p.name).first()
        if not exists:
            db.add(p)
            added += 1
    if added:
        db.commit()
        print(f"已写入 {added} 条新策略（按名称幂等，已存在则跳过）")
    else:
        print("策略均已存在，跳过")

    db.close()
    print("种子数据初始化完成。")


if __name__ == "__main__":
    main()
