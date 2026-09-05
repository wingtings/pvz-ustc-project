import { Node } from '/engine/Node.js'

export default class LaneEnemy extends Node {
  ready() {
    const c = this.config || {}
    this.startX = Number(c.startX)
    this.overlapX = Number(c.overlapX)
    this.baseSpeed = Number(c.baseSpeed)
    this.heaterMultiplier = Number(c.heaterMultiplier)
    this.iceMultiplier = Number(c.iceMultiplier)
    this.leftBound = Number(c.leftBound)
    this.iced = false
    this.insideHeater = false
    this.activeHeaterCount = 0
    this.speedMultiplier = 1
    this.effectiveSpeed = this.baseSpeed
    this.distanceTravelled = 0
    this._recomputeSpeed()
  }

  _recomputeSpeed() {
    const x = this.gameObject?.x ?? this.startX
    const heaters = this.findByTag('heater')
    this.activeHeaterCount = heaters.filter((heater) => {
      if (!heater.gameObject) return false
      const radius = Number(heater.config?.radius || 0)
      return Math.abs(heater.gameObject.x - x) <= radius
    }).length
    this.insideHeater = this.activeHeaterCount > 0
    this.speedMultiplier = this.iced
      ? this.iceMultiplier
      : (this.insideHeater ? this.heaterMultiplier : 1)
    this.effectiveSpeed = this.baseSpeed * this.speedMultiplier

    if (this.visualObject?.setFillStyle) {
      const color = this.iced ? 0x4f9ee8 : (this.insideHeater ? 0xc75c36 : 0x8d3434)
      this.visualObject.setFillStyle(color)
    }
  }

  update(dt) {
    if (!this.gameObject) return
    this._recomputeSpeed()
    const delta = this.effectiveSpeed * dt
    this.gameObject.x -= delta
    this.distanceTravelled += delta
    if (this.gameObject.x < this.leftBound) this.gameObject.x = this.startX
    this._recomputeSpeed()
  }

  placeInOverlap() {
    if (this.gameObject) this.gameObject.x = this.overlapX
    this._recomputeSpeed()
  }

  toggleIce() {
    this.iced = !this.iced
    this._recomputeSpeed()
  }

  resetEnemy() {
    if (this.gameObject) this.gameObject.x = this.startX
    this.iced = false
    this.distanceTravelled = 0
    this._recomputeSpeed()
  }

  runtimeState() {
    return {
      x: this.gameObject?.x ?? null,
      baseSpeed: this.baseSpeed,
      speedMultiplier: this.speedMultiplier,
      effectiveSpeed: this.effectiveSpeed,
      activeHeaterCount: this.activeHeaterCount,
      insideHeater: this.insideHeater,
      iced: this.iced,
      distanceTravelled: this.distanceTravelled,
    }
  }
}
