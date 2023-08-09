UnSubscribeToEventSubscription = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:b="http://docs.oasis-open.org/wsn/b-2">
    <soap:Header/>
    <soap:Body>
    <b:Unsubscribe>
    <!--You may enter ANY elements at this point-->
    </b:Unsubscribe>
    </soap:Body>
    </soap:Envelope>"""

GetDeviceInformation = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver10/device/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:GetDeviceInformation/>
   </soap:Body>
</soap:Envelope>"""

GetCurrentPTZ = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver20/ptz/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:GetStatus>
         <wsdl:ProfileToken>MediaProfile00000</wsdl:ProfileToken>
      </wsdl:GetStatus>
   </soap:Body>
</soap:Envelope>"""

GetRTSPURL = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver10/media/wsdl" xmlns:sch="http://www.onvif.org/ver10/schema">
   <soap:Header/>
   <soap:Body>
      <wsdl:GetStreamUri>
         <wsdl:StreamSetup>
            <sch:Stream>?</sch:Stream>
            <sch:Transport>
               <sch:Protocol>rtsp</sch:Protocol>
               <!--Optional:-->
               <sch:Tunnel/>
            </sch:Transport>
            <!--You may enter ANY elements at this point-->
         </wsdl:StreamSetup>
         <wsdl:ProfileToken>MediaProfile00000</wsdl:ProfileToken>
      </wsdl:GetStreamUri>
   </soap:Body>
</soap:Envelope>"""

restartCamera = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver10/device/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:SystemReboot/>
   </soap:Body>
</soap:Envelope>"""

absolutePtzMove = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver20/ptz/wsdl" xmlns:sch="http://www.onvif.org/ver10/schema">
   <soap:Header/>
   <soap:Body>
      <wsdl:AbsoluteMove>
         <wsdl:ProfileToken>MediaProfile00000</wsdl:ProfileToken>
         <wsdl:Position>
            <sch:PanTilt x="{RP1}" y="{RP2}"/>
            <sch:Zoom x="{RP3}}"/>
         </wsdl:Position>
         <wsdl:Speed>
            <sch:PanTilt x="{RP4}" y="{RP5}"/>
            <sch:Zoom x="{RP6}"/>
         </wsdl:Speed>
      </wsdl:AbsoluteMove>
   </soap:Body>
</soap:Envelope>"""

continiousPtzMove = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver20/ptz/wsdl" xmlns:sch="http://www.onvif.org/ver10/schema">
   <soap:Header/>
   <soap:Body>
      <wsdl:ContinuousMove>
         <wsdl:ProfileToken>MediaProfile00000</wsdl:ProfileToken>
         <wsdl:Velocity>
            <sch:PanTilt x="{RP1}" y="{RP2}"/>
            <sch:Zoom x="{RP3}"/>
         </wsdl:Velocity>
      </wsdl:ContinuousMove>
   </soap:Body>
</soap:Envelope>"""