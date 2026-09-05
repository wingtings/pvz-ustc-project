import { Node } from '/engine/Node.js'

export default class MechanicsLab extends Node {
  ready() {
    const c = this.config || {}
    this.initialGpa = Number(c.initialGpa)
    this.insurancePenalty = Number(c.insurancePenalty)
    this.ddlPenalty = Number(c.ddlPenalty)
    this.ddlPenaltyCap = Number(c.ddlPenaltyCap)
    this.enemy = this.getChild('Enemy')
    this.gpa = this.initialGpa
    this.insuranceTriggerCount = 0
    this.ddlSuccessCount = 0
    this.ddlBlockedCount = 0
    this.lastEvent = 'ready'

    for (const heater of this.findByTag('heater')) {
      heater.visualObject?.setAlpha(0.72)
    }

    this._createHud()
    this._renderHud()
  }

  _createHud() {
    const container = document.getElementById('game-container')
    if (!container) return
    this.hud = document.createElement('div')
    Object.assign(this.hud.style, {
      position: 'absolute',
      left: '22px',
      top: '18px',
      width: '916px',
      color: '#edf8e9',
      background: 'rgba(5, 18, 13, 0.86)',
      border: '1px solid rgba(207, 235, 199, 0.45)',
      borderRadius: '10px',
      padding: '12px 16px',
      fontSize: '15px',
      lineHeight: '1.55',
      pointerEvents: 'none',
      zIndex: '10',
    })
    container.appendChild(this.hud)
  }

  _recordInsurance() {
    this.insuranceTriggerCount += 1
    this.gpa = Math.max(0, this.gpa - this.insurancePenalty)
    this.lastEvent = 'insurance_triggered'
  }

  _recordDdlSuccess() {
    if (this.ddlSuccessCount < this.ddlPenaltyCap) {
      this.ddlSuccessCount += 1
      this.gpa = Math.max(0, this.gpa - this.ddlPenalty)
      this.lastEvent = 'ddl_success_counted'
    } else {
      this.lastEvent = 'ddl_success_ignored_at_cap'
    }
  }

  _recordDdlBlocked() {
    this.ddlBlockedCount += 1
    this.lastEvent = 'ddl_blocked_no_penalty'
  }

  _resetLab() {
    this.gpa = this.initialGpa
    this.insuranceTriggerCount = 0
    this.ddlSuccessCount = 0
    this.ddlBlockedCount = 0
    this.lastEvent = 'reset'
    this.enemy?.resetEnemy?.()
  }

  update() {
    const input = this.sceneTree.inputMap
    if (input) {
      if (input.isPressed('place_overlap')) {
        this.enemy?.placeInOverlap?.()
        this.lastEvent = 'enemy_placed_in_overlap'
      }
      if (input.isPressed('toggle_ice')) {
        this.enemy?.toggleIce?.()
        this.lastEvent = this.enemy?.iced ? 'ice_enabled' : 'ice_disabled'
      }
      if (input.isPressed('trigger_insurance')) this._recordInsurance()
      if (input.isPressed('ddl_success')) this._recordDdlSuccess()
      if (input.isPressed('ddl_blocked')) this._recordDdlBlocked()
      if (input.isPressed('reset_lab')) this._resetLab()
    }
    this._renderHud()
  }

  _renderHud() {
    if (!this.hud) return
    const enemy = this.enemy?.runtimeState?.() || {}
    this.hud.innerHTML = [
      '<strong>PvZ-USTC v0.4 机制沙盘</strong>',
      `GPA ${this.gpa}　保险 ${this.insuranceTriggerCount} 次　DDL 成功 ${this.ddlSuccessCount}/${this.ddlPenaltyCap}　被阻止 ${this.ddlBlockedCount}`,
      `敌人速度 ${Number(enemy.speedMultiplier || 0).toFixed(2)}×　范围内暖气片 ${enemy.activeHeaterCount || 0}　寒冰 ${enemy.iced ? '开' : '关'}`,
      '<span style="color:#bdd5c4">P 重叠范围　I 寒冰　Q 保险　D 成功空投　F 阻止空投　R 重置</span>',
    ].join('<br>')
  }

  destroy() {
    this.hud?.remove()
    this.hud = null
  }

  runtimeState() {
    return {
      gpa: this.gpa,
      initialGpa: this.initialGpa,
      insurancePenalty: this.insurancePenalty,
      insuranceTriggerCount: this.insuranceTriggerCount,
      ddlPenalty: this.ddlPenalty,
      ddlPenaltyCap: this.ddlPenaltyCap,
      ddlSuccessCount: this.ddlSuccessCount,
      ddlBlockedCount: this.ddlBlockedCount,
      lastEvent: this.lastEvent,
      enemy: this.enemy?.runtimeState?.() || null,
    }
  }
}
