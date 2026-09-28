import React, { useEffect, useRef } from 'react'

export default function Chart({ option, height = 320 }) {
  const ref = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!window.echarts || !el) return
    if (!chartRef.current) chartRef.current = window.echarts.init(el)
    chartRef.current.setOption(option, true)
  }, [option])

  useEffect(() => {
    const onResize = () => chartRef.current && chartRef.current.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      if (chartRef.current) { chartRef.current.dispose(); chartRef.current = null }
    }
  }, [])

  return <div ref={ref} style={{ width: '100%', height }} />
}
