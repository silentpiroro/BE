import * as React from "react"

const Tabs = React.forwardRef(({ className, value, onValueChange, ...props }, ref) => {
  const [activeTab, setActiveTab] = React.useState(value || "")
  
  React.useEffect(() => {
    if (value !== undefined) {
      setActiveTab(value)
    }
  }, [value])
  
  const handleTabChange = (newValue) => {
    setActiveTab(newValue)
    if (onValueChange) {
      onValueChange(newValue)
    }
  }
  
  return (
    <div
      data-state={activeTab}
      ref={ref}
      className={`${className}`}
      {...props}
    />
  )
})
Tabs.displayName = "Tabs"

const TabsList = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={`inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground ${className}`}
    role="tablist"
    {...props}
  />
))
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef(({ className, value, ...props }, ref) => {
  const tabsContext = React.useContext(React.createContext({ activeTab: null }))
  const isActive = tabsContext?.activeTab === value
  
  return (
    <button
      ref={ref}
      role="tab"
      className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm ${className}`}
      data-state={isActive ? "active" : "inactive"}
      {...props}
    />
  )
})
TabsTrigger.displayName = "TabsTrigger"

const TabsContent = React.forwardRef(({ className, value, ...props }, ref) => {
  const tabsContext = React.useContext(React.createContext({ activeTab: null }))
  const isActive = tabsContext?.activeTab === value
  
  if (!isActive && !props.forceMount) {
    return null
  }
  
  return (
    <div
      ref={ref}
      role="tabpanel"
      className={`mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${className}`}
      data-state={isActive ? "active" : "inactive"}
      tabIndex={isActive ? 0 : -1}
      {...props}
    />
  )
})
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }
