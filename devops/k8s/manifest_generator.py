"""
DevPilot AI - Kubernetes Manifest Generator
Synthesizes production-ready, hardened Kubernetes manifests including
Deployment (with PSS compliance), Service, ConfigMap, HPA, and Ingress.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class K8sManifestSet:
    deployment_yaml: str
    service_yaml: str
    configmap_yaml: str
    hpa_yaml: Optional[str]
    ingress_yaml: Optional[str]
    all_manifests_combined: str
    app_name: str
    namespace: str
    container_port: int
    replicas: int

    @property
    def combined_yaml(self) -> str:
        return self.all_manifests_combined


class K8sManifestGenerator:
    """Generates Kubernetes YAML manifests adhering to Cloud Native best practices."""

    def generate(
        self,
        app_name: str = "devpilot-app",
        namespace: str = "default",
        image: Optional[str] = None,
        tag: str = "latest",
        replicas: int = 2,
        container_port: int = 8000,
        port: Optional[int] = None,
        service_port: int = 80,
        service_type: str = "ClusterIP",
        env_vars: Optional[Dict[str, str]] = None,
        cpu_request: str = "200m",
        cpu_limit: str = "500m",
        memory_request: str = "256Mi",
        memory_limit: str = "512Mi",
        health_path: str = "/api/health",
        enable_hpa: bool = True,
        min_replicas: int = 2,
        max_replicas: int = 10,
        enable_ingress: bool = True,
        ingress_host: Optional[str] = None
    ) -> K8sManifestSet:
        """Generates a complete set of validated Kubernetes resources."""
        clean_name = app_name.lower().replace("_", "-").replace(" ", "-")
        clean_ns = namespace.lower().strip() or "default"
        target_image = image or f"devpilot/{clean_name}:{tag}"
        target_host = ingress_host or f"{clean_name}.devpilot.internal"
        actual_port = port if port is not None else container_port

        # 1. ConfigMap
        config_data = env_vars or {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "info",
            "PORT": str(actual_port)
        }
        config_entries = "\n".join([f"    {k}: \"{v}\"" for k, v in config_data.items()])
        configmap_yaml = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {clean_name}-config
  namespace: {clean_ns}
  labels:
    app.kubernetes.io/name: {clean_name}
    app.kubernetes.io/part-of: devpilot-ai
data:
{config_entries}
"""

        # 2. Deployment (Pod Security Standards Restricted compliance)
        deployment_yaml = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {clean_name}
  namespace: {clean_ns}
  labels:
    app.kubernetes.io/name: {clean_name}
    app.kubernetes.io/part-of: devpilot-ai
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app.kubernetes.io/name: {clean_name}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {clean_name}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: {clean_name}
        image: {target_image}
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: {actual_port}
          protocol: TCP
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: "{cpu_request}"
            memory: "{memory_request}"
          limits:
            cpu: "{cpu_limit}"
            memory: "{memory_limit}"
        envFrom:
        - configMapRef:
            name: {clean_name}-config
        livenessProbe:
          httpGet:
            path: {health_path}
            port: {actual_port}
          initialDelaySeconds: 15
          periodSeconds: 20
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: {health_path}
            port: {actual_port}
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 2
"""

        # 3. Service
        service_yaml = f"""apiVersion: v1
kind: Service
metadata:
  name: {clean_name}-service
  namespace: {clean_ns}
  labels:
    app.kubernetes.io/name: {clean_name}
    app.kubernetes.io/part-of: devpilot-ai
spec:
  type: {service_type}
  selector:
    app.kubernetes.io/name: {clean_name}
  ports:
  - name: http
    port: {service_port}
    targetPort: {actual_port}
    protocol: TCP
"""

        # 4. HPA (HorizontalPodAutoscaler)
        hpa_yaml = None
        if enable_hpa:
            hpa_yaml = f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {clean_name}-hpa
  namespace: {clean_ns}
  labels:
    app.kubernetes.io/name: {clean_name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {clean_name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""

        # 5. Ingress
        ingress_yaml = None
        if enable_ingress:
            ingress_yaml = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {clean_name}-ingress
  namespace: {clean_ns}
  labels:
    app.kubernetes.io/name: {clean_name}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  rules:
  - host: {target_host}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {clean_name}-service
            port:
              number: {service_port}
"""

        # Combined multi-document manifest
        docs = [configmap_yaml, deployment_yaml, service_yaml]
        if hpa_yaml:
            docs.append(hpa_yaml)
        if ingress_yaml:
            docs.append(ingress_yaml)

        all_combined = "\n---\n".join([d.strip() for d in docs]) + "\n"

        return K8sManifestSet(
            deployment_yaml=deployment_yaml.strip() + "\n",
            service_yaml=service_yaml.strip() + "\n",
            configmap_yaml=configmap_yaml.strip() + "\n",
            hpa_yaml=hpa_yaml.strip() + "\n" if hpa_yaml else None,
            ingress_yaml=ingress_yaml.strip() + "\n" if ingress_yaml else None,
            all_manifests_combined=all_combined,
            app_name=clean_name,
            namespace=clean_ns,
            container_port=actual_port,
            replicas=replicas
        )


k8s_manifest_generator = K8sManifestGenerator()
