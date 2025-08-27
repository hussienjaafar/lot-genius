# Page snapshot

```yaml
- generic [ref=e1]:
    - navigation [ref=e2]:
        - generic [ref=e5]:
            - heading "Lot Genius" [level=1] [ref=e6]
            - generic [ref=e7]:
                - link "Home" [ref=e8] [cursor=pointer]:
                    - /url: /
                - link "Calibration" [ref=e9] [cursor=pointer]:
                    - /url: /calibration
    - main [ref=e11]:
        - heading "Lot Genius" [level=1] [ref=e12]
        - generic [ref=e13]:
            - generic [ref=e14]:
                - generic [ref=e15]:
                    - checkbox "Direct Backend Mode" [ref=e16]
                    - generic [ref=e17]: Direct Backend Mode
                - generic [ref=e18]: Using Next.js API proxy
            - generic [ref=e19]:
                - button "Optimize Lot" [ref=e20] [cursor=pointer]
                - button "Pipeline (SSE)" [active] [ref=e21] [cursor=pointer]
        - generic [ref=e23]:
            - generic [ref=e25]:
                - heading "Pipeline Streaming" [level=2] [ref=e26]
                - paragraph [ref=e27]: Monitor real-time progress of the optimization pipeline
            - generic [ref=e29]:
                - generic [ref=e30]:
                    - generic [ref=e31]: Items CSV (Required)
                    - generic [ref=e33] [cursor=pointer]:
                        - img [ref=e34] [cursor=pointer]
                        - paragraph [ref=e36] [cursor=pointer]: Click to browse or drag and drop a file here
                        - paragraph [ref=e37] [cursor=pointer]: "Accepts: .csv"
                - button "Run Pipeline" [disabled] [ref=e38]
                - paragraph [ref=e40]: No events yet...
    - alert [ref=e41]
```
