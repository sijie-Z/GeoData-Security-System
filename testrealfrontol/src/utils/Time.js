import i18n from '@/locales/index.js'

const t = (key) => i18n.global.t(key)

const Time = {
  now() {
    const date = new Date()
    const yyyy = date.getFullYear()
    const MM = String(date.getMonth() + 1).padStart(2, '0')
    const dd = String(date.getDate()).padStart(2, '0')
    const HH = String(date.getHours()).padStart(2, '0')
    const mm = String(date.getMinutes()).padStart(2, '0')
    const ss = String(date.getSeconds()).padStart(2, '0')
    return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`
  },

  timeSub(startTime, endTime) {
    const startDate = new Date(startTime)
    const endDate = new Date(endTime)

    let expire = false
    let expireText = t('time.expiresIn')
    let duration = endDate - startDate
    if (duration < 0) {
      expire = true
      expireText = t('time.expired')
      duration = -duration
    }

    const day = Math.floor(duration / (24 * 60 * 60 * 1000))
    const hour = Math.floor((duration / (60 * 60 * 1000)) % 24)
    const minute = Math.floor((duration / (60 * 1000)) % 60)
    const second = Math.floor(duration / 1000) % 60

    return {
      expire,
      startDate,
      endDate,
      day,
      hour,
      minute,
      second,
      remark: `${expireText} ${day} ${t('time.days')} ${hour} ${t('time.hours')} ${minute} ${t('time.minutes')} ${second} ${t('time.seconds')}`,
    }
  },
}

export default Time
