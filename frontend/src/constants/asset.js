// 资产状态（与后端 AssetStatus 对应）
// maintenance / scrapped 为预留扩展，本期不开放操作入口，仅做展示
export const ASSET_STATUS = {
  available: { label: '空闲', tag: 'success' },
  in_use: { label: '已领用', tag: 'warning' },
  maintenance: { label: '维修中', tag: 'info' },
  scrapped: { label: '已报废', tag: 'danger' },
}

// 资产类型（与后端 AssetType 对应）
export const ASSET_TYPE = {
  computer: '电脑',
  phone: '手机',
  monitor: '显示器',
  peripheral: '外设',
  furniture: '办公家具',
  other: '其他',
}

// 流转动作（与后端 LogAction 对应）
export const LOG_ACTION = {
  checkout: '领用',
  return: '归还',
  transfer: '调拨',
  maintenance_in: '送修',
  maintenance_out: '修好',
  scrap: '报废',
}

// 流转动作对应的标签颜色（'' 为默认色）
export const LOG_ACTION_TAG = {
  checkout: 'success',
  return: 'warning',
  transfer: '',
  maintenance_in: 'info',
  maintenance_out: '',
  scrap: 'danger',
}

// 状态机：当前状态下允许的流转动作
// 本期仅开放 checkout / return；后续扩展送修、修好、报废时在此登记即可，
// 流转弹窗组件会根据 ACTION_FIELDS 自动渲染表单。
export const STATUS_ACTIONS = {
  available: ['checkout'],
  in_use: ['return'],
  maintenance: [],
  scrapped: [],
}

// 各动作需要的表单字段（employee_id=是否选择员工）
export const ACTION_META = {
  checkout: {
    label: '领用',
    needEmployee: true,
    lockEmployee: false,
    successText: '领用成功',
  },
  return: {
    label: '归还',
    needEmployee: true,
    lockEmployee: true,
    successText: '归还成功',
  },
}

export const EMPLOYEE_STATUS = {
  1: { label: '在职', tag: 'success' },
  0: { label: '离职', tag: 'info' },
}
