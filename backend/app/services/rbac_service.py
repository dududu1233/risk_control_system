from sqlalchemy.orm import Session

from app.models.auth import RolePermission, UserRole


def get_user_permissions(db: Session, user) -> set:
    perms: set = set()
    for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all():
        for rp in db.query(RolePermission).filter(RolePermission.role_id == ur.role_id).all():
            perms.add(rp.permission_code)
    return perms


def get_user_role_names(db: Session, user) -> list:
    from app.models.auth import Role

    names = []
    for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all():
        role = db.query(Role).filter(Role.id == ur.role_id).first()
        if role:
            names.append(role.name)
    return names
