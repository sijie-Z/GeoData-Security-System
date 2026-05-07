const  Time={
    now(){
        let date=new Date()

        let yyyy=date.getFullYear()
        let MM=String(date.getMonth()+1).padStart(2,'0')
        let dd=String(date.getDate()).padStart(2,'0')
        let HH = String(date.getHours()).padStart(2, '0')
        let mm = String(date.getMinutes()).padStart(2, '0')
        let ss = String(date.getSeconds()).padStart(2, '0')

        return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`
    },

    timeSub(startTime,endTime){
        let startDate = new Date(startTime)
        let endDate = new Date(endTime)

        let expire = false
        let expireText ='距离过期还差'
        let  duration=endDate-startDate
        if (duration<0)
        {
            expire = true
            expireText='已过期'
            duration=-duration
        }

        let day=Math.floor(duration/(24 * 60 * 60 * 1000))
        let hour = Math.floor((duration / (60 * 60 * 1000)) % 24)
        let minute = Math.floor((duration / (60 * 1000)) % 60)
        let second = Math.floor(duration / 1000) % 60

        return{
            expire,
            startDate,
            endDate,
            day,
            hour,
            minute,
            second,
            remark: `${expireText} ${day} 天 ${hour} 小时 ${minute} 分钟 ${second} 秒`,
        }
    }
}
export default Time

